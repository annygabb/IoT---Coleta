-- Proposta aditiva, NÃO aplicada à instância hospedada por esta entrega.
-- Revisar e executar antes de publicar a função com /platform-ingest.
CREATE TABLE IF NOT EXISTS public.smartwaste_canonical_events (
  fog_id text NOT NULL REFERENCES public.smartwaste_credentials(fog_id),
  id_mensagem uuid NOT NULL,
  device_id text NOT NULL,
  measured_at timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  payload jsonb NOT NULL CHECK (jsonb_typeof(payload)='object'),
  PRIMARY KEY (fog_id,id_mensagem)
);
CREATE INDEX IF NOT EXISTS smartwaste_canonical_measurement_time
  ON public.smartwaste_canonical_events(fog_id,measured_at DESC,id_mensagem);
CREATE INDEX IF NOT EXISTS smartwaste_canonical_device_time
  ON public.smartwaste_canonical_events(fog_id,device_id,measured_at DESC);
CREATE INDEX IF NOT EXISTS smartwaste_events_measurement_time
  ON public.smartwaste_events(fog_id,simulated_at DESC,event_id);
ALTER TABLE public.smartwaste_canonical_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.smartwaste_canonical_events FROM anon,authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.smartwaste_canonical_events TO service_role;
