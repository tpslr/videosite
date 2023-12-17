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


CREATE TYPE public.usertype AS ENUM (
    'anonymous',
    'normal',
    'admin'
);


SET default_tablespace = '';


SET default_table_access_method = heap;


CREATE TABLE public.comments (
    id integer NOT NULL,
    owner integer,
    content text,
    video text
);


CREATE SEQUENCE public.comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.comments_id_seq OWNED BY public.comments.id;


CREATE TABLE public.tokens (
    uid integer,
    token text NOT NULL,
    expires timestamp without time zone NOT NULL
);


CREATE TABLE public.users (
    uid integer NOT NULL,
    type public.usertype NOT NULL,
    username text,
    join_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    password text
);


CREATE SEQUENCE public.users_uid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.users_uid_seq OWNED BY public.users.uid;


CREATE TABLE public.videos (
    id text NOT NULL,
    owner integer,
    views integer DEFAULT 0 NOT NULL,
    private boolean NOT NULL,
    duration integer NOT NULL,
    title text NOT NULL,
    upload_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


CREATE TABLE public.views (
    video_id text,
    user_id integer,
    count integer DEFAULT 0 NOT NULL
);


ALTER TABLE ONLY public.comments ALTER COLUMN id SET DEFAULT nextval('public.comments_id_seq'::regclass);

ALTER TABLE ONLY public.users ALTER COLUMN uid SET DEFAULT nextval('public.users_uid_seq'::regclass);


ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (uid);


ALTER TABLE ONLY public.videos
    ADD CONSTRAINT videos_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_owner_fkey FOREIGN KEY (owner) REFERENCES public.users(uid);


ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_video_fkey FOREIGN KEY (video) REFERENCES public.videos(id);


ALTER TABLE ONLY public.tokens
    ADD CONSTRAINT tokens_uid_fkey FOREIGN KEY (uid) REFERENCES public.users(uid);


ALTER TABLE ONLY public.videos
    ADD CONSTRAINT videos_owner_fkey FOREIGN KEY (owner) REFERENCES public.users(uid);


ALTER TABLE ONLY public.views
    ADD CONSTRAINT views_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(uid);


ALTER TABLE ONLY public.views
    ADD CONSTRAINT views_video_id_fkey FOREIGN KEY (video_id) REFERENCES public.videos(id);
