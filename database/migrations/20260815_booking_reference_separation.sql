-- Phase 30 P0: separate ERP booking number from carrier booking reference.
-- Safe for existing rows: adds a nullable carrier reference only.

ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS carrier_booking_no TEXT;

CREATE INDEX IF NOT EXISTS idx_bookings_carrier_booking_no
    ON bookings(carrier_booking_no);
