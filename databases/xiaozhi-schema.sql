--
-- PostgreSQL database dump
--

\restrict f6S7Lhl4zhuxbEdh87dSsQxtDAXJCrZgLKQajPsgF3yUIMCeRuMyyROz4sHX6IL

-- Dumped from database version 16.13 (Debian 16.13-1.pgdg12+1)
-- Dumped by pg_dump version 16.13 (Debian 16.13-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.groups (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying NOT NULL,
    description text,
    servers json,
    owner character varying,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: mcp_servers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mcp_servers (
    name character varying NOT NULL,
    type character varying,
    url character varying,
    command character varying,
    args text,
    env text,
    headers text,
    enabled boolean DEFAULT true NOT NULL,
    owner character varying,
    keep_alive_interval integer,
    tools text,
    prompts text,
    options text,
    openapi text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: system_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_config (
    id character varying DEFAULT 'default'::character varying NOT NULL,
    routing text,
    install text,
    smart_routing text,
    mcp_router text,
    modelscope text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    username character varying NOT NULL,
    password character varying NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: vector_embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vector_embeddings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    content_type character varying NOT NULL,
    content_id character varying NOT NULL,
    text_content text NOT NULL,
    metadata text NOT NULL,
    dimensions integer NOT NULL,
    model character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    embedding public.vector
);


--
-- Name: xiaozhi_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.xiaozhi_config (
    id character varying DEFAULT 'default'::character varying NOT NULL,
    enabled boolean DEFAULT false NOT NULL,
    load_balancing text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: xiaozhi_endpoints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.xiaozhi_endpoints (
    id character varying NOT NULL,
    name character varying NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    websocket_url character varying,
    description text,
    group_id character varying,
    use_smart_routing boolean DEFAULT false NOT NULL,
    reconnect text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    last_connected timestamp without time zone,
    status character varying DEFAULT 'disconnected'::character varying NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: xiaozhi_endpoints PK_20498e0a5ba0676bc02af8a9b44; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.xiaozhi_endpoints
    ADD CONSTRAINT "PK_20498e0a5ba0676bc02af8a9b44" PRIMARY KEY (id);


--
-- Name: mcp_servers PK_2ee0138f3dd9575eedd37f2405f; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcp_servers
    ADD CONSTRAINT "PK_2ee0138f3dd9575eedd37f2405f" PRIMARY KEY (name);


--
-- Name: groups PK_659d1483316afb28afd3a90646e; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT "PK_659d1483316afb28afd3a90646e" PRIMARY KEY (id);


--
-- Name: xiaozhi_config PK_88a31c7d78f8b151af3570acce8; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.xiaozhi_config
    ADD CONSTRAINT "PK_88a31c7d78f8b151af3570acce8" PRIMARY KEY (id);


--
-- Name: users PK_a3ffb1c0c8416b9fc6f907b7433; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT "PK_a3ffb1c0c8416b9fc6f907b7433" PRIMARY KEY (id);


--
-- Name: vector_embeddings PK_b42dabe33bbb7b2aca4426e6e08; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vector_embeddings
    ADD CONSTRAINT "PK_b42dabe33bbb7b2aca4426e6e08" PRIMARY KEY (id);


--
-- Name: system_config PK_db4e70ac0d27e588176e9bb44a0; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT "PK_db4e70ac0d27e588176e9bb44a0" PRIMARY KEY (id);


--
-- Name: users UQ_fe0bb3f6520ee0469504521e710; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE (username);


--
-- Name: IDX_fe0bb3f6520ee0469504521e71; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_fe0bb3f6520ee0469504521e71" ON public.users USING btree (username);


--
-- PostgreSQL database dump complete
--

\unrestrict f6S7Lhl4zhuxbEdh87dSsQxtDAXJCrZgLKQajPsgF3yUIMCeRuMyyROz4sHX6IL

