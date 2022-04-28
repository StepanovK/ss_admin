CREATE TABLE users
                   (id integer primary key NOT NULL,
                   first_name varchar NOT NULL,
                   last_name varchar NOT NULL,
                   birth_date integer,
                   subscription_date integer,
                   is_active boolean NOT NULL
                   );


CREATE TABLE subscribers
                   (user_id integer NOT NULL,
                   "date" varchar NOT NULL,
                   is_subscribed boolean NOT NULL,
                   FOREIGN KEY ("user_id") REFERENCES users(id) ON DELETE CASCADE
                   );


CREATE TABLE attachments
                   (id serial primary key,
                   type varchar NOT NULL,
                   description varchar,
                   preview_url varchar,
                   url varchar,
                   file_name varchar,
                   user_id integer,
                   FOREIGN KEY (user_id) REFERENCES users(id)
                   );


CREATE TABLE posts
                   (id integer primary key NOT NULL,
                   user_id integer,
                   signed_id integer,
                   "date" varchar NOT NULL,
                   "text" text NOT NULL,
                   is_deleted boolean NOT NULL,
                   FOREIGN KEY ("user_id") REFERENCES users(id)
                  );


CREATE TABLE posts_attachments
                   (post_id integer NOT NULL,
                   attachment_id integer NOT NULL,
                   is_deleted boolean NOT NULL,
                   FOREIGN KEY ("post_id") REFERENCES posts(id) ON DELETE CASCADE,
                   FOREIGN KEY ("attachment_id") REFERENCES attachments(id) ON DELETE CASCADE
                   );


CREATE TABLE posts_likes
                   (post_id integer NOT NULL,
                   user_id integer NOT NULL,
                   "date" integer NOT NULL,
                   is_deleted boolean NOT NULL,
                   FOREIGN KEY ("user_id") REFERENCES users(id) ON DELETE CASCADE,
                   FOREIGN KEY ("post_id") REFERENCES posts(id) ON DELETE CASCADE
                   );


CREATE TABLE posts_hashtags
                   (post_id integer NOT NULL,
                   hashtag varchar(100) NOT NULL,
                   FOREIGN KEY ("post_id") REFERENCES posts(id) ON DELETE CASCADE
                   );


CREATE TABLE comments
                   (id integer primary key NOT NULL,
                   user_id integer,
                   group_id integer,
                   post_id integer NOT NULL,
                   replied_comment_id integer,
                   replied_to_user_id integer,
                   "date" integer NOT NULL,
                   "text" text NOT NULL,
                   is_deleted boolean NOT NULL,
                   FOREIGN KEY ("replied_comment_id") REFERENCES comments(id),
                   FOREIGN KEY ("user_id") REFERENCES users(id),
                   FOREIGN KEY ("post_id") REFERENCES posts(id) ON DELETE CASCADE
                   );


CREATE TABLE comments_attachments
                   (comment_id integer NOT NULL,
                   attachment_id integer NOT NULL,
                   is_deleted boolean NOT NULL,
                   FOREIGN KEY ("comment_id") REFERENCES comments(id) ON DELETE CASCADE,
                   FOREIGN KEY ("attachment_id") REFERENCES attachments(id) ON DELETE CASCADE
                   );


CREATE TABLE comments_likes
                   (comment_id integer NOT NULL,
                   user_id integer NOT NULL,
                   "date" integer NOT NULL,
                   is_deleted boolean NOT NULL,
                   FOREIGN KEY ("user_id") REFERENCES users(id) ON DELETE CASCADE,
                   FOREIGN KEY ("comment_id") REFERENCES comments(id) ON DELETE CASCADE
                   );


CREATE TABLE suggested_posts
                   (id integer primary key NOT NULL,
                   user_id integer,
                   signed_id integer,
                   "date" integer NOT NULL,
                   "text" text NOT NULL,
                   is_deleted boolean NOT NULL,
                   is_posted boolean NOT NULL,
                   is_rejected boolean NOT NULL,
                   admin_id integer,
                   FOREIGN KEY ("user_id") REFERENCES users(id)
                  );


CREATE TABLE suggested_posts_attachments
                   (post_id integer NOT NULL,
                   attachment_id integer NOT NULL,
                   is_deleted boolean NOT NULL,
                   FOREIGN KEY ("post_id") REFERENCES suggested_posts(id) ON DELETE CASCADE,
                   FOREIGN KEY ("attachment_id") REFERENCES attachments(id) ON DELETE CASCADE
                   );


CREATE TABLE suggested_posts_hashtags
                   (post_id integer NOT NULL,
                   hashtag varchar(100) NOT NULL,
                   FOREIGN KEY ("post_id") REFERENCES suggested_posts(id) ON DELETE CASCADE
                   );