-- Referência do schema já publicado. Não contém o token privado.
CREATE TABLE IF NOT EXISTS public.smartwaste_credentials (
 token_hash text PRIMARY KEY CHECK (token_hash ~ '^[a-f0-9]{64}$'),
 fog_id text NOT NULL UNIQUE CHECK(length(fog_id) BETWEEN 1 AND 100),
 enabled boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.smartwaste_events (
 fog_id text NOT NULL REFERENCES public.smartwaste_credentials(fog_id),
 event_id text NOT NULL CHECK(length(event_id) BETWEEN 1 AND 100),
 run_id text NOT NULL CHECK(length(run_id) BETWEEN 1 AND 100),
 device_id text NOT NULL, bin_id text NOT NULL,
 sequence bigint NOT NULL CHECK(sequence>=0),
 simulated_at timestamptz NOT NULL, emitted_at timestamptz NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now(),
 fill_pct double precision NOT NULL CHECK(fill_pct BETWEEN 0 AND 120),
 temperature_c double precision NOT NULL CHECK(temperature_c BETWEEN -50 AND 150),
 battery_pct double precision NOT NULL CHECK(battery_pct BETWEEN 0 AND 100),
 operational_state text NOT NULL CHECK(operational_state IN('NORMAL','ATENCAO','ALTA','CRITICA','TRANSBORDO','EM_COLETA')),
 sensor_status text NOT NULL CHECK(sensor_status IN('ONLINE','STALE','OFFLINE','FAULTY')),
 firmware_version text NOT NULL,
 PRIMARY KEY(fog_id,event_id)
);
CREATE INDEX IF NOT EXISTS smartwaste_events_run_time ON public.smartwaste_events(fog_id,run_id,received_at DESC);
ALTER TABLE public.smartwaste_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.smartwaste_credentials ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.smartwaste_events, public.smartwaste_credentials FROM anon,authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.smartwaste_events, public.smartwaste_credentials TO service_role;
