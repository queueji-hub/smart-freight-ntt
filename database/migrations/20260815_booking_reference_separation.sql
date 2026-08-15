-- Phase 30 P0: Booking reference separation / duplicate protection.
--
-- booking_no is always the ERP/internal Booking number.
-- carrier_booking_no stores a carrier-provided Booking reference.
-- This migration is backward-compatible: it adds a nullable carrier reference
-- and protects legacy callers that still pass carrier numbers via booking_no.

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
    v_is_internal BOOLEAN;
    v_requested TEXT;
BEGIN
    v_requested := btrim(COALESCE(NEW.booking_no, ''));
    IF v_requested = '' THEN
        RETURN NEW;
    END IF;

    v_is_internal := v_requested ~ '^BK-[0-9]{4}-[0-9]{4}$';

    -- Legacy UI may still send a carrier reference through booking_no.
    -- Preserve it as carrier_booking_no and always allocate a real internal BK number.
    IF NOT v_is_internal THEN
        IF NEW.carrier_booking_no IS NULL OR btrim(NEW.carrier_booking_no) = '' THEN
            NEW.carrier_booking_no := v_requested;
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
        RETURN NEW;
    END IF;

    -- A requested internal BK number is preserved unless it already exists.
    IF EXISTS (
        SELECT 1 FROM bookings b WHERE b.booking_no = v_requested
    ) THEN
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
