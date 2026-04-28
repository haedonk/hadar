--
-- PostgreSQL database dump
--


-- Dumped from database version 16.13 (Debian 16.13-1.pgdg12+1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)


--
-- Name: appliances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.appliances (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    category text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    manufacturer text,
    notes text
);


--
-- Name: device_rename; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.device_rename (
    id bigint NOT NULL,
    from_id uuid NOT NULL,
    to_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    notes text
);


--
-- Name: device_rename_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.device_rename_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: device_rename_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.device_rename_id_seq OWNED BY public.device_rename.id;


--
-- Name: devices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.devices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    device_label text NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    renamed_at timestamp with time zone,
    device_type text DEFAULT 'plug'::text NOT NULL,
    description text DEFAULT ''::text NOT NULL
);


--
-- Name: energy_readings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.energy_readings (
    id bigint NOT NULL,
    device_id uuid NOT NULL,
    load_group_id uuid,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    power_watts numeric(10,3),
    energy_kwh numeric(12,6),
    voltage_volts numeric(6,2),
    current_amps numeric(6,3),
    power_factor numeric(4,3),
    linkquality integer,
    source text DEFAULT 'zigbee2mqtt'::text
);


--
-- Name: energy_readings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.energy_readings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: energy_readings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.energy_readings_id_seq OWNED BY public.energy_readings.id;


--
-- Name: error_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.error_logs (
    id bigint NOT NULL,
    source text NOT NULL,
    error_type text NOT NULL,
    message text NOT NULL,
    details text,
    device_id uuid,
    topic text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: error_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.error_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: error_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.error_logs_id_seq OWNED BY public.error_logs.id;


--
-- Name: load_group_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.load_group_members (
    load_group_id uuid NOT NULL,
    appliance_id uuid NOT NULL,
    added_at timestamp with time zone DEFAULT now() NOT NULL,
    removed_at timestamp with time zone
);


--
-- Name: load_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.load_groups (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    location text,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: plug_load_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.plug_load_group (
    device_id uuid NOT NULL,
    load_group_id uuid NOT NULL,
    assigned_at timestamp with time zone DEFAULT now() NOT NULL,
    assigned_by text,
    assignment_note text
);


--
-- Name: plug_load_group_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.plug_load_group_history (
    id bigint NOT NULL,
    device_id uuid NOT NULL,
    load_group_id uuid NOT NULL,
    assigned_at timestamp with time zone NOT NULL,
    unassigned_at timestamp with time zone DEFAULT now() NOT NULL,
    changed_by text,
    change_reason text
);


--
-- Name: plug_load_group_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.plug_load_group_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: plug_load_group_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.plug_load_group_history_id_seq OWNED BY public.plug_load_group_history.id;


--
-- Name: temperature_readings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.temperature_readings (
    id bigint NOT NULL,
    device_id uuid NOT NULL,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    battery numeric(3,0),
    humidity numeric(5,2),
    pressure numeric(7,2),
    temperature numeric(5,2),
    linkquality integer,
    source text DEFAULT 'zigbee2mqtt'::text
);


--
-- Name: temperature_readings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.temperature_readings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: temperature_readings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.temperature_readings_id_seq OWNED BY public.temperature_readings.id;


--
-- Name: topic_payload_identifier; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topic_payload_identifier (
    id bigint NOT NULL,
    topic text NOT NULL,
    type text,
    payload jsonb NOT NULL
);


--
-- Name: topic_payload_identifier_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.topic_payload_identifier_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: topic_payload_identifier_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.topic_payload_identifier_id_seq OWNED BY public.topic_payload_identifier.id;


--
-- Name: device_rename id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_rename ALTER COLUMN id SET DEFAULT nextval('public.device_rename_id_seq'::regclass);



--
-- Name: energy_readings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.energy_readings ALTER COLUMN id SET DEFAULT nextval('public.energy_readings_id_seq'::regclass);


--
-- Name: error_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error_logs ALTER COLUMN id SET DEFAULT nextval('public.error_logs_id_seq'::regclass);


--
-- Name: plug_load_group_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plug_load_group_history ALTER COLUMN id SET DEFAULT nextval('public.plug_load_group_history_id_seq'::regclass);


--
-- Name: temperature_readings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.temperature_readings ALTER COLUMN id SET DEFAULT nextval('public.temperature_readings_id_seq'::regclass);


--
-- Name: topic_payload_identifier id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic_payload_identifier ALTER COLUMN id SET DEFAULT nextval('public.topic_payload_identifier_id_seq'::regclass);


--
-- Name: appliances appliances_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.appliances
    ADD CONSTRAINT appliances_name_key UNIQUE (name);


--
-- Name: appliances appliances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.appliances
    ADD CONSTRAINT appliances_pkey PRIMARY KEY (id);


--
-- Name: device_rename device_rename_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_rename
    ADD CONSTRAINT device_rename_pkey PRIMARY KEY (id);



--
-- Name: energy_readings energy_readings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.energy_readings
    ADD CONSTRAINT energy_readings_pkey PRIMARY KEY (id);


--
-- Name: error_logs error_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_pkey PRIMARY KEY (id);


--
-- Name: load_group_members load_group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.load_group_members
    ADD CONSTRAINT load_group_members_pkey PRIMARY KEY (load_group_id, appliance_id, added_at);


--
-- Name: load_groups load_groups_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.load_groups
    ADD CONSTRAINT load_groups_name_key UNIQUE (name);


--
-- Name: load_groups load_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.load_groups
    ADD CONSTRAINT load_groups_pkey PRIMARY KEY (id);


--
-- Name: plug_load_group_history plug_load_group_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plug_load_group_history
    ADD CONSTRAINT plug_load_group_history_pkey PRIMARY KEY (id);


--
-- Name: plug_load_group plug_load_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plug_load_group
    ADD CONSTRAINT plug_load_group_pkey PRIMARY KEY (device_id);


--
-- Name: devices plugs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT plugs_pkey PRIMARY KEY (id);


--
-- Name: devices plugs_plug_label_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT plugs_plug_label_key UNIQUE (device_label);


--
-- Name: temperature_readings temperature_readings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.temperature_readings
    ADD CONSTRAINT temperature_readings_pkey PRIMARY KEY (id);


--
-- Name: topic_payload_identifier topic_payload_identifier_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic_payload_identifier
    ADD CONSTRAINT topic_payload_identifier_pkey PRIMARY KEY (id);


--
-- Name: topic_payload_identifier topic_payload_identifier_topic_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic_payload_identifier
    ADD CONSTRAINT topic_payload_identifier_topic_key UNIQUE (topic);


--
-- Name: idx_device_load_group_group; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_device_load_group_group ON public.plug_load_group USING btree (load_group_id);


--
-- Name: idx_device_load_group_hist_device_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_device_load_group_hist_device_time ON public.plug_load_group_history USING btree (device_id, unassigned_at DESC);


--
-- Name: idx_energy_device_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_energy_device_ts ON public.energy_readings USING btree (device_id, ts DESC);


--
-- Name: idx_energy_group_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_energy_group_ts ON public.energy_readings USING btree (load_group_id, ts DESC);


--
-- Name: idx_group_members_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_group_members_active ON public.load_group_members USING btree (load_group_id) WHERE (removed_at IS NULL);


--
-- Name: idx_temp_device_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_temp_device_time ON public.temperature_readings USING btree (device_id, ts DESC);


--
-- Name: uq_appliance_one_active_group; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_appliance_one_active_group ON public.load_group_members USING btree (appliance_id) WHERE (removed_at IS NULL);


--
-- Name: device_rename device_rename_from_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_rename
    ADD CONSTRAINT device_rename_from_id_fkey FOREIGN KEY (from_id) REFERENCES public.devices(id);


--
-- Name: device_rename device_rename_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_rename
    ADD CONSTRAINT device_rename_to_id_fkey FOREIGN KEY (to_id) REFERENCES public.devices(id);


--
-- Name: energy_readings energy_readings_load_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.energy_readings
    ADD CONSTRAINT energy_readings_load_group_id_fkey FOREIGN KEY (load_group_id) REFERENCES public.load_groups(id) ON DELETE RESTRICT;


--
-- Name: energy_readings energy_readings_plug_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.energy_readings
    ADD CONSTRAINT energy_readings_plug_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE CASCADE;


--
-- Name: error_logs error_logs_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id);


--
-- Name: load_group_members load_group_members_appliance_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.load_group_members
    ADD CONSTRAINT load_group_members_appliance_id_fkey FOREIGN KEY (appliance_id) REFERENCES public.appliances(id) ON DELETE CASCADE;


--
-- Name: load_group_members load_group_members_load_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.load_group_members
    ADD CONSTRAINT load_group_members_load_group_id_fkey FOREIGN KEY (load_group_id) REFERENCES public.load_groups(id) ON DELETE CASCADE;


--
-- Name: plug_load_group_history plug_load_group_history_load_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plug_load_group_history
    ADD CONSTRAINT plug_load_group_history_load_group_id_fkey FOREIGN KEY (load_group_id) REFERENCES public.load_groups(id) ON DELETE RESTRICT;


--
-- Name: plug_load_group_history plug_load_group_history_plug_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plug_load_group_history
    ADD CONSTRAINT plug_load_group_history_plug_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE CASCADE;


--
-- Name: plug_load_group plug_load_group_load_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plug_load_group
    ADD CONSTRAINT plug_load_group_load_group_id_fkey FOREIGN KEY (load_group_id) REFERENCES public.load_groups(id) ON DELETE RESTRICT;


--
-- Name: plug_load_group plug_load_group_plug_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plug_load_group
    ADD CONSTRAINT plug_load_group_plug_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE CASCADE;


--
-- Name: temperature_readings temperature_readings_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.temperature_readings
    ADD CONSTRAINT temperature_readings_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id);


--
-- PostgreSQL database dump complete
--


