CREATE TABLE `app_settings` (
	`id` integer PRIMARY KEY DEFAULT 1 NOT NULL,
	`post_download_action` text DEFAULT 'both' NOT NULL,
	`book_retention_days` integer DEFAULT 30 NOT NULL,
	`time_format` text DEFAULT '24h' NOT NULL,
	`date_format` text DEFAULT 'eur' NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `booklore_settings` (
	`id` integer PRIMARY KEY DEFAULT 1 NOT NULL,
	`enabled` integer DEFAULT false NOT NULL,
	`base_url` text,
	`access_token` text,
	`refresh_token` text,
	`access_token_expires_at` integer,
	`refresh_token_expires_at` integer,
	`last_token_refresh` integer,
	`library_id` integer,
	`path_id` integer,
	`auto_upload` integer DEFAULT true NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `books` (
	`md5` text PRIMARY KEY NOT NULL,
	`title` text NOT NULL,
	`authors` text,
	`publisher` text,
	`description` text,
	`cover_url` text,
	`filename` text,
	`language` text,
	`format` text,
	`size` integer,
	`year` integer,
	`content_type` text,
	`source` text,
	`saves` integer,
	`lists` integer,
	`issues` integer,
	`search_count` integer DEFAULT 0 NOT NULL,
	`first_seen_at` integer NOT NULL,
	`last_seen_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `downloads` (
	`md5` text PRIMARY KEY NOT NULL,
	`title` text NOT NULL,
	`filename` text,
	`author` text,
	`publisher` text,
	`language` text,
	`format` text,
	`year` integer,
	`status` text NOT NULL,
	`size` integer,
	`downloaded_bytes` integer DEFAULT 0,
	`progress` real DEFAULT 0,
	`speed` text,
	`eta` integer,
	`temp_path` text,
	`final_path` text,
	`error` text,
	`retry_count` integer DEFAULT 0,
	`delayed_retry_count` integer DEFAULT 0,
	`next_retry_at` integer,
	`downloads_left` integer,
	`downloads_per_day` integer,
	`quota_checked_at` integer,
	`queued_at` integer NOT NULL,
	`started_at` integer,
	`completed_at` integer,
	`path_index` integer,
	`domain_index` integer,
	`upload_status` text,
	`uploaded_at` integer,
	`upload_error` text
);
--> statement-breakpoint
CREATE TABLE `search_cache` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`query_hash` text NOT NULL,
	`query` text NOT NULL,
	`results` text NOT NULL,
	`pagination` text NOT NULL,
	`cached_at` integer NOT NULL,
	`expires_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `search_cache_query_hash_unique` ON `search_cache` (`query_hash`);