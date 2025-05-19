create database game_finder_bot;

create table users(
    id bigint primary key,
    username varchar(255) not null,
    full_name varchar(255) not null,
    created_at timestamp default current_timestamp
);

create table games(
    id int primary key,
    name varchar(255) not null,
    short_description text not null,
    description text not null,
    developers json default '[]',
    genres json default '[]',
    categories json default '[]',
    platforms json default '{}',
    recommendations int,
    supported_languages text,
    is_free boolean,
    normalized text
);

create table recommendation_history(
    id serial primary key,
    user_id bigint not null,
    genres json default '[]',
    categories json default '[]',
    created_at timestamp default now()
);

create table mute_games
(
    user_id bigint not null,
    game_id int    not null,
    primary key (user_id, game_id)
)