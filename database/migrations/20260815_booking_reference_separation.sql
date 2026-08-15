-- Phase 30 P0: Booking reference separation / duplicate protection.
--
-- Existing booking_no remains the ERP's internal unique booking number.
-- A carrier-provided reference belongs in carrier_booking_no.
-- The application may still send the legacy carrier reference in booking_no;
-- the trigger safely converts that value to carrier_booking_no when it would
-- collide with an existing booking_no, then allocates a new ERP booking_no.

ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS carrier_booking_no TEXT;

CREATE INDEX IF NOT EXISTS idx_bookings_carrier_booking_no
    ON bookings(carrier_booking_no);

CREATE OR REPLACE FUNCTION bookings_normalize_duplicate_reference()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_yymm TEXT;
    v_running INTEGER;
    v_internal_no TEXT;
BEGIN
    IF NEW.booking_no IS NULL OR btrim(NEW.booking_no) = '' THEN
        RETURN NEW;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM bookings b
        WHERE b.booking_no = NEW.booking_no
    ) THEN
        IF NEW.carrier_booking_no IS NULL OR btrim(NEW.carrier_booking_no) = '' THEN
            NEW.carrier_booking_no := btrim(NEW.booking_no);
        END IF;

        v_yymm := to_char(COALESCE(NEW.etd, CURRENT_DATE), 'YYMM');

        INSERT INTO doc_counters (doc_type, yymm, last_running)
        VALUES ('BK', v_yymm, 1)
        ON CONFLICT (doc_type, yymm)
        DO UPDATE SET last_running = doc_counters.last_running + 1
        RETURNING last_running INTO v_running;

        v_internal_no := 'BK-' || v_yymm || '-' || lpad(v_running::TEXT, 4, '0');

        WHILE EXISTS (
            SELECT 1 FROM bookings b WHERE b.booking_no = v_internal_no
        ) LOOP
            INSERT INTO doc_counters (doc_type, yymm, last_running)
            VALUES ('BK', v_yymm, 1)
            ON CONFLICT (doc_type, yymm)
            DO UPDATE SET last_running = doc_counters.last_running + 1
            RETURNING last_running INTO v_running;

            v_internal_no := 'BK-' || v_yymm || '-' || lpad(v_running::TEXT, 4, '0');
        END LOOP;

        NEW.booking_no := v_internal_no;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_bookings_normalize_duplicate_reference ON bookings;

CREATE TRIGGER trg_bookings_normalize_duplicate_reference
BEFORE INSERT ON bookings
FOR EACH ROW
EXECUTE FUNCTION bookings_normalize_duplicate_reference();

CREATE UNIQUE INDEX IF NOT EXISTS uq_bookings_tenant_carrier_booking_no
    ON bookings(tenant_id, carrier_booking_no)
    WHERE carrier_booking_no IS NOT NULL AND btrim(carrier_booking_no) <> '';
