-- BigQuery and Redshift compatible SQL for Data Vault model creation

-- Hubs
CREATE TABLE IF NOT EXISTS hub_user (
    user_hashkey VARCHAR(64) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    load_timestamp TIMESTAMP NOT NULL,
    record_source VARCHAR(255) NOT NULL,
    PRIMARY KEY (user_hashkey)
);

CREATE TABLE IF NOT EXISTS hub_content (
    content_hashkey VARCHAR(64) NOT NULL,
    content_id VARCHAR(255) NOT NULL,
    load_timestamp TIMESTAMP NOT NULL,
    record_source VARCHAR(255) NOT NULL,
    PRIMARY KEY (content_hashkey)
);

-- Links
CREATE TABLE IF NOT EXISTS link_user_interaction (
    link_hashkey VARCHAR(64) NOT NULL,
    user_hashkey VARCHAR(64) NOT NULL,
    content_hashkey VARCHAR(64) NOT NULL,
    interaction_timestamp TIMESTAMP NOT NULL,
    load_timestamp TIMESTAMP NOT NULL,
    record_source VARCHAR(255) NOT NULL,
    PRIMARY KEY (link_hashkey),
    FOREIGN KEY (user_hashkey) REFERENCES hub_user(user_hashkey),
    FOREIGN KEY (content_hashkey) REFERENCES hub_content(content_hashkey)
);

-- Satellites
CREATE TABLE IF NOT EXISTS satellite_user_details (
    user_hashkey VARCHAR(64) NOT NULL,
    load_timestamp TIMESTAMP NOT NULL,
    email VARCHAR(255),
    age INT,
    PRIMARY KEY (user_hashkey, load_timestamp),
    FOREIGN KEY (user_hashkey) REFERENCES hub_user(user_hashkey)
);

CREATE TABLE IF NOT EXISTS satellite_content_details (
    content_hashkey VARCHAR(64) NOT NULL,
    load_timestamp TIMESTAMP NOT NULL,
    title VARCHAR(255),
    category VARCHAR(255),
    PRIMARY KEY (content_hashkey, load_timestamp),
    FOREIGN KEY (content_hashkey) REFERENCES hub_content(content_hashkey)
);
