---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        -   label: "Linkedin"
            icon: "fab fa-fw fa-linkedin"
            url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/pg-stat-statements/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/pg-stat-statements/banner.jpeg
title: "Unlock the Power of PostgreSQL: A Comprehensive Guide to pg_stat_statements"
tags:
    - PostgreSQL

---

Are you looking to optimize the performance of your PostgreSQL database? Look no further than pg_stat_statements, a built-in extension that provides invaluable insights into your database's performance. This comprehensive guide will empower you to enable pg_stat_statements, identify slow queries, and optimize them for maximum efficiency. We'll delve into the intricacies of reading results from pg_stat_statements and discuss best practices for its effective use. Whether you're a database administrator or a developer, this guide will equip you with the knowledge to make your PostgreSQL database faster and more efficient.


### Introduction

Welcome to a deep dive into PostgreSQL performance tuning, where we unravel the capabilities of the `pg_stat_statements` module. This powerful extension is an indispensable tool for any serious PostgreSQL user, offering comprehensive statistics on all executed SQL statements. With `pg_stat_statements`, you gain visibility into query performance, allowing you to swiftly identify and rectify slow-running queries.

Enabling `pg_stat_statements` is your first step towards database optimization. Once activated, it meticulously tracks execution frequencies, execution times, and more, for each query. This granular data is crucial for diagnosing performance issues and forms the basis of our optimization strategies.

Throughout this blog post, we will walk you through:

- **Enabling `pg_stat_statements`**: We'll provide a step-by-step guide on how to enable this extension within your PostgreSQL environment.
- **Identifying Slow Queries**: Learn how to use `pg_stat_statements` to detect queries that are negatively impacting your database's performance.
- **Optimizing Queries**: We'll share best practices and techniques for query optimization, ensuring your database runs at peak efficiency.

Whether you're a seasoned database administrator or a developer eager to enhance your PostgreSQL prowess, this guide will serve as a valuable resource. By the end of this post, you'll be well-equipped to make informed decisions that will significantly improve the performance of your PostgreSQL database.



### Enabling pg_stat_statements

#### Explanation of pg_stat_statements as a PostgreSQL extension

`pg_stat_statements` is an official PostgreSQL extension that provides a means to track execution statistics of all SQL statements executed by a server. It's invaluable for identifying performance bottlenecks and offers a granular view of query activity, which can be used for further optimization.

#### Steps to enable pg_stat_statements

To enable `pg_stat_statements`, you need to perform the following steps:

1. **Modifying postgresql.conf**:

   Locate your `postgresql.conf` file, which is usually found in the data directory of your PostgreSQL installation. Insert the following line to include `pg_stat_statements` in the list of preloaded libraries:

   ```plaintext
   shared_preload_libraries = 'pg_stat_statements'
   ```

   This directive is necessary because `pg_stat_statements` must be loaded into shared memory at server start to function correctly.

2. **Restarting the PostgreSQL server**:

   For the changes to take effect, you must restart the PostgreSQL service. This can typically be done using a command like `sudo service postgresql restart`, but the exact command may vary based on your system's service management.

3. **Enabling pg_stat_statements for a specific database**:

   Connect to the database where you want to use `pg_stat_statements` and run:

   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
   ```

   This SQL command will create the necessary objects for the extension within the current database context.

By following these steps, `pg_stat_statements` will be enabled, and you can start using it to monitor and improve the performance of your PostgreSQL queries.



### Using pg_stat_statements for Query Optimization

#### Explanation of the `pg_stat_statements` View and Its Columns

The `pg_stat_statements` module provides a means to track execution statistics of all SQL statements executed by a PostgreSQL server. When enabled, it offers insights into performance by capturing a wide array of data points. Here's a breakdown of its key columns:

- `query`: Text of a representative statement.
- `queryid`: Internal hash code, computed from the statement's parse tree, serving as a unique identifier.
- `userid`: OID of the user who executed the statement.
- `dbid`: OID of the database where the statement was executed.
- `calls`: Number of times the statement was executed.
- `total_time`: Total time spent in the statement, in milliseconds.
- `rows`: Total number of rows retrieved or affected.
- `shared_blks_hit`: Number of shared block cache hits.
- `shared_blks_read`: Number of shared blocks read from disk.
- `shared_blks_dirtied`: Number of shared blocks dirtied.
- `shared_blks_written`: Number of shared blocks written to disk.

#### Identifying Slow-Running Queries

To pinpoint slow-running queries, you can sort the data by `total_time` to see which queries are consuming the most time. For example:

```sql
SELECT query, total_time, calls, rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

This query will list the top 10 time-consuming queries, allowing you to focus optimization efforts where they are most needed.

#### The Concept of Query Normalization in pg_stat_statements

Query normalization in `pg_stat_statements` refers to the deconstruction of executed SQL statements into a generalized form. This process strips constants and literals from the query, replacing them with placeholders, thus grouping similar queries together even if their literal values differ. This aids in identifying patterns of resource-intensive queries that could benefit from optimization strategies such as indexing or query rewriting.



### Reading Results from pg_stat_statements

#### Understanding the Various Columns in the `pg_stat_statements` View

The `pg_stat_statements` module provides a means to track execution statistics of all SQL statements executed by a server. The view `pg_stat_statements` is created upon loading the module and contains one row for each distinct executable statement (regardless of the number of times it has been executed) with various statistics. Here are the key columns:

- **`userid`**: The OID of the user who executed the statement.
- **`dbid`**: The OID of the database in which the statement was executed.
- **`queryid`**: A hash code computed from the statement's text.
- **`query`**: Text of a representative statement.
- **`calls`**: Number of times the statement was executed.
- **`total_time`**: Total time spent in the statement, in milliseconds.
- **`min_time`**: Minimum time spent in the statement, in milliseconds.
- **`max_time`**: Maximum time spent in the statement, in milliseconds.
- **`mean_time`**: Mean time spent in the statement, in milliseconds.
- **`stddev_time`**: Population standard deviation of time spent in the statement, in milliseconds.
- **`rows`**: Total number of rows retrieved or affected by the statement.
- **`shared_blks_hit`**: Total number of shared block cache hits by the statement.
- **`shared_blks_read`**: Total number of shared blocks read by the statement.
- **`shared_blks_dirtied`**: Total number of shared blocks dirtied by the statement.
- **`shared_blks_written`**: Total number of shared blocks written by the statement.
- **`local_blks_hit`**: Total number of local block cache hits by the statement.
- **`local_blks_read`**: Total number of local blocks read by the statement.
- **`local_blks_dirtied`**: Total number of local blocks dirtied by the statement.
- **`local_blks_written`**: Total number of local blocks written by the statement.
- **`temp_blks_read`**: Total number of temp blocks read by the statement.
- **`temp_blks_written`**: Total number of temp blocks written by the statement.
- **`blk_read_time`**: Total time the statement spent reading blocks, in milliseconds (if track_io_timing is enabled).
- **`blk_write_time`**: Total time the statement spent writing blocks, in milliseconds (if track_io_timing is enabled).

#### Selecting Top Queries Based on Different Criteria

To analyze the performance of your queries, you can select the top queries based on various criteria such as execution time, frequency, and resource consumption:

- **By Execution Time**: 
  ```sql
  SELECT query, total_time, calls, mean_time
  FROM pg_stat_statements
  ORDER BY total_time DESC
  LIMIT 10;
  ```

- **By Frequency**:
  ```sql
  SELECT query, calls
  FROM pg_stat_statements
  ORDER BY calls DESC
  LIMIT 10;
  ```

- **By Rows Retrieved**:
  ```sql
  SELECT query, rows
  FROM pg_stat_statements
  ORDER BY rows DESC
  LIMIT 10;
  ```

- **By Shared Block Reads** (indicative of disk I/O):
  ```sql
  SELECT query, shared_blks_read
  FROM pg_stat_statements
  ORDER BY shared_blks_read DESC
  LIMIT 10;
  ```

These queries will help you identify which statements are consuming the most time, being executed most frequently, retrieving the most rows, or causing the most disk I/O, respectively.

For more details, refer to the PostgreSQL documentation on `pg_stat_statements`.



### Improving Query Performance

#### Steps to Improve the Performance of Slow Queries Using `pg_stat_statements`

1. **Identify the Slow Queries**: Utilize `pg_stat_statements` to pinpoint the queries that are consuming excessive time or resources. This module provides a means to track execution statistics of all SQL statements executed by a server.

2. **Analyze the Query Plan**: Use `EXPLAIN` along with the slow queries to get their execution plans. This will reveal how PostgreSQL plans to execute the query, including details about joins, sorts, and indexes.

3. **Optimize the Query**: Refine the query based on the insights gained from the execution plan. This could involve:
    - **Index Optimization**: Create new indexes or modify existing ones to reduce the query execution time.
    - **Query Rewriting**: Simplify complex queries, eliminate subqueries, and consider alternative ways to achieve the same result more efficiently.
    - **Materialized Views**: Implement materialized views to store the result of a computationally heavy query and refresh it periodically.

4. **Monitor the Results**: Continuously monitor the query performance post-optimization. `pg_stat_statements` can be reset to clear the statistics and observe the changes from a fresh state.

#### How to Monitor Index Usage

Monitoring index usage is crucial for maintaining query performance. The `pg_stat_user_indexes` and `pg_statio_user_indexes` views can be used to get detailed index usage statistics.

To monitor index usage, consider the following query:

```sql
SELECT 
pg_stat_user_indexes.relname, pg_stat_user_indexes.indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
JOIN pg_statio_user_indexes USING (indexrelid)
WHERE idx_scan < 50 AND idx_tup_read > 0;
```

This query filters out indexes that are not being used often (less than 50 scans) but have read tuples, indicating potential underutilization.

#### The Importance of Tracking Performance Over Time

Performance tracking over time is essential to understand the long-term trends and impacts of any changes. Use tools like `pgBadger` to analyze PostgreSQL logs for a comprehensive report on the database's performance, which can help in proactive optimization and capacity planning.



### Best Practices and Pitfalls

#### Best Practices for Using `pg_stat_statements` Effectively

- **Enable `pg_stat_statements` on all production databases:** This module provides a means to track execution statistics of all SQL statements executed by a server. Enabling it on production databases can help in identifying inefficient queries and understanding the workload pattern.

- **Set the `pg_stat_statements.track` to `all`:** This configuration ensures comprehensive monitoring. It includes tracking of top-level statements, as well as those within procedures and functions, providing a complete picture of database activity.

- **Adjust the `pg_stat_statements.max` appropriately:** This setting controls the number of statements tracked by `pg_stat_statements`. Setting it too high may lead to excessive resource usage, while too low may not capture enough data for meaningful analysis. Balance is key.

- **Regularly review the `pg_stat_statements` view:** This view holds the data on SQL statement execution, and regular analysis can help in proactive performance tuning and identifying long-running queries.

- **Leverage `pg_stat_statements` for performance troubleshooting:** When facing performance issues, this module can be instrumental in pinpointing problematic queries. It provides insights into execution counts, total time, rows affected, and more.

#### Potential Pitfalls and How to Avoid Them

- **Avoid disabling `pg_stat_statements`:** Disabling this module means losing visibility into query performance, which is crucial for maintaining an efficient database system.

- **Do not set `pg_stat_statements.track` to `none`:** This would prevent the collection of any query statistics, rendering the module ineffective.

- **Be cautious with `pg_stat_statements.max` value:** Setting this too low may result in older statements being discarded before they can be analyzed, while too high a value can consume more memory.

- **Don't overlook the `pg_stat_statements` view:** Neglecting the data here can lead to missed opportunities for optimization and delayed identification of issues.

- **Test changes in a non-production environment first:** Before using `pg_stat_statements` data to make changes, validate the impact in a development or staging environment to prevent potential disruptions in production.

For more detailed information and best practices, refer to the PostgreSQL documentation and reputable community resources:

- PostgreSQL Documentation: pg_stat_statements
- Depesz Blog: Using pg_stat_statements to Improve PostgreSQL Performance



### Conclusion

Throughout this guide, we've explored the pivotal role of `pg_stat_statements` in PostgreSQL performance tuning. This extension is indispensable for database administrators and developers alike, providing a granular view into query execution and performance metrics.

Enabling `pg_stat_statements` is straightforward, yet it unlocks a wealth of information. By examining key columns such as `total_time`, `min_time`, `max_time`, and `calls`, you can pinpoint inefficient queries that are prime candidates for optimization.

Moreover, `pg_stat_statements` offers a historical perspective, allowing you to track changes in query performance over time. This is crucial for assessing the impact of your optimization efforts and for proactive performance management.

As you continue to manage and optimize your PostgreSQL databases, remember that `pg_stat_statements` is more than just a tool—it's a gateway to a deeper understanding of your database's inner workings. It empowers you to make data-driven decisions that enhance the overall performance and scalability of your applications.

We urge you to integrate `pg_stat_statements` into your regular database maintenance routines. Experiment with its features, customize your analysis, and watch as your database's efficiency soars. With `pg_stat_statements`, you're not just maintaining a database; you're mastering it.


