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
    overlay_image: /assets/images/mongo-id-in-postgresql/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/mongo-id-in-postgresql/banner.jpeg
title: "Simulating MongoDB's ObjectID in PostgreSQL: A Comprehensive Guide"
tags:
    - Mongo ID
    - PostgreSQL

---

This article provides a comprehensive guide to simulating MongoDB's ObjectID in PostgreSQL. It begins by introducing MongoDB's ObjectID and explaining the need for simulating it in PostgreSQL. The article then delves into the structure and components of MongoDB's ObjectID, as well as the advantages and disadvantages of using PostgreSQL's UUID as an alternative. The main focus of the article is on designing and implementing a custom ID generation function in PostgreSQL that mimics the functionality of MongoDB's ObjectID. The article provides step-by-step instructions on how to create and test the custom function, as well as how to use it in PostgreSQL tables and applications. Finally, the article discusses potential considerations and limitations of using a custom ID generation function, and concludes with a summary of the key points and suggestions for further exploration.


## Introduction

MongoDB's ObjectID is a pivotal component in the identification of documents within a MongoDB collection. This 12-byte identifier is not just a random string; it's a carefully constructed sequence that provides a wealth of information and guarantees uniqueness across documents.

### Composition of MongoDB's ObjectID

MongoDB's ObjectID is a 12-byte hexadecimal string that serves as a primary key for documents in a collection. It is designed to be unique across different machines and moments in time, ensuring that every document can be uniquely identified. Here's a more detailed breakdown of its structure:

1. **Timestamp (4 bytes)**: The ObjectID begins with a 4-byte timestamp, representing the creation time of the document. This is measured in seconds since the Unix epoch (January 1, 1970). The use of a timestamp helps in sorting documents by creation time without additional queries.

2. **Machine Identifier (3 bytes)**: Following the timestamp, the next 3 bytes are a unique identifier for the machine or device. While this often uses the machine's MAC address for uniqueness, it can also be a hash of the machine's hostname or IP address if the MAC address is not available.

3. **Process Identifier (2 bytes)**: The two bytes after the machine identifier are used for the process ID. This ensures that ObjectIDs generated simultaneously on the same machine are unique.

4. **Random Counter (3 bytes)**: The final 3 bytes are a random value that starts with a random number at the process start. It increments with each ObjectID generation. This counter adds another layer of uniqueness to the ObjectID, especially for documents created in rapid succession within the same process.

The ObjectID is not only a means of identification but also provides a mechanism for sharding. In a sharded MongoDB cluster, ObjectIDs can be used to distribute documents across different shards, aiding in load balancing and horizontal scaling.

the ObjectID is a carefully constructed identifier that leverages time, machine, and process-specific data, along with a random component, to ensure the uniqueness and efficient distribution of documents within a MongoDB database.

### Significance of ObjectID

The design of the ObjectID allows MongoDB to generate unique identifiers without a centralized authority, which is crucial for distributed databases. The inclusion of a timestamp also facilitates the ordering of documents by creation time without additional fields or indexes.

## PostgreSQL's UUID as an Alternative

PostgreSQL's implementation of the UUID offers a robust alternative to MongoDB's ObjectID for unique identifier generation. Here's a deeper dive into the technical aspects of PostgreSQL's UUID:

- **Technical Specification**: A UUID is a 128-bit number, typically displayed in a 32-character hexadecimal format. It is divided into five groups separated by hyphens, as in `550e8400-e29b-41d4-a716-446655440000`.

- **Versioning and Variants**: PostgreSQL primarily uses version 4 UUIDs, which are randomly generated. There are other versions of UUIDs, such as version 1 which includes the timestamp and MAC address, but version 4 is preferred for its unpredictability and lower risk of collision.

- **Indexing and Storage**: When using UUIDs as primary keys, it's important to consider the indexing strategy. B-tree indexes, the default in PostgreSQL, can handle UUIDs efficiently. However, UUIDs are larger than traditional integer IDs, which can lead to increased storage requirements and potentially slower index performance.

- **Generation Methods**: PostgreSQL does not generate UUIDs by default. To generate UUIDs, you need to install the `uuid-ossp` extension. This extension provides multiple functions to generate UUIDs, including `uuid_generate_v4()` which is based on random numbers.

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
SELECT uuid_generate_v4();
```

- **Advantages**:
    - **Global Uniqueness**: The probability of generating duplicate UUIDs is negligible, making them safe for distributed systems where central coordination is not feasible.
    - **Anonymity**: Unlike ObjectIDs, which can reveal information about the creation time and originating machine, UUIDs do not expose such details, thus providing better privacy.

- **Disadvantages**:
    - **Verbosity**: UUIDs are long and can be less user-friendly when exposed in interfaces or URLs.
    - **No Inherent Order**: UUIDs do not have a natural ordering, which can be a disadvantage when order of creation is significant.

In conclusion, PostgreSQL's UUIDs are a powerful tool for ensuring global uniqueness without the need for a central authority. They are particularly useful in distributed databases and microservices architectures. However, the choice between UUIDs and ObjectIDs should be made based on the specific needs of the application, considering factors like the need for order, human readability, and the importance of metadata such as timestamps.

## Designing a Custom ID Generation Function in PostgreSQL

In this section, we delve deeper into the intricacies of creating a custom ID generation function in PostgreSQL. Our focus is on ensuring that the IDs generated are unique, the performance is optimized, and the function integrates well with the existing database schema.

### Objective

The goal is to emulate the behavior of MongoDB's ObjectID feature within PostgreSQL. We aim to create a function that generates 12-byte identifiers, which are unique and suitable for use as primary keys in database tables.

### Function Design

The design of our custom ID generation function revolves around three critical aspects:

- **Uniqueness**: To prevent ID collisions and ensure data integrity, the function must produce distinct identifiers for each record.
- **Performance**: The function must be optimized for speed and efficiency to minimize the impact on database operations.
- **Integration**: It should fit seamlessly within the current database schema and be straightforward to implement in queries and application code.

### Step-by-Step Implementation

With a firm grasp of the design criteria, we can outline the steps for implementing the custom ID generation function:

1. **Create the Function**: Utilize PostgreSQL's PL/pgSQL to craft the function. It should accept no parameters and return a bytea type representing the 12-byte identifier.
2. **Generate Timestamp**: Extract the current timestamp using `EXTRACT(EPOCH FROM now())` and cast it to an integer to get a 4-byte representation of time since the Unix epoch.
3. **Generate Machine Identifier**: Derive a 3-byte machine identifier from a consistent server-specific detail, such as a hash of the MAC address.
4. **Generate Process Identifier**: Fetch the current backend process ID with `pg_backend_pid()` and truncate or hash it to fit into 2 bytes.
5. **Generate Random Counter**: Implement a 3-byte counter that increments with each function call, ensuring a unique value for concurrent operations.
6. **Combine Components**: Assemble the timestamp, machine identifier, process identifier, and counter into a single 12-byte identifier.
7. **Return the Result**: Output the final identifier, ensuring it's in the correct bytea format for PostgreSQL.

### Using the Custom ID in PostgreSQL

After rigorous testing, integrate the custom ID function into your database:

1. **Create a Table**: Define a new table or alter an existing one to use the custom ID function for its primary key column.
2. **Insert Data**: When inserting new records, the function will automatically generate a unique identifier for each.
3. **Query Data**: Leverage the custom ID to locate and manipulate records efficiently.

### Implementing and Testing the Custom ID Function

The custom ID function is designed to generate a unique identifier for database records. This guide will walk you through the process of creating and testing this function in a PostgreSQL environment.

#### Step 1: Create the Function

To begin, you'll need to define the function in SQL. The function `generate_object_id` will return a byte array (`bytea`) that represents the generated ID. Here's the SQL code to create the function:

```sql
CREATE FUNCTION generate_object_id() RETURNS bytea AS $$
DECLARE
  time_component bigint;
  process_id bigint;
  result bytea := '';
BEGIN
  -- Extract the current timestamp in seconds since the Unix epoch
  SELECT FLOOR(EXTRACT(EPOCH FROM clock_timestamp())) INTO time_component;
  -- Retrieve the current backend process ID
  SELECT pg_backend_pid() INTO process_id;
  -- Concatenate the time component, machine identifier, process ID, and a random counter
  result := result || lpad(to_hex(time_component), 8, '0');
  result := result || substring(md5(CAST(inet_server_addr() AS text)) FROM 1 FOR 6);
  result := result || lpad(to_hex(process_id), 4, '0');
  result := result || lpad(to_hex(nextval('objectid_sequence')::bigint), 6, '0');
  -- Return the constructed byte array
  RETURN result;
END;
$$ LANGUAGE plpgsql VOLATILE;
```

#### Step 2: Create a Sequence

Next, you'll need a sequence to generate a unique counter for the ID. This sequence will be incremented each time the function is called to ensure uniqueness:

```sql
CREATE SEQUENCE objectid_sequence;
```

#### Step 3: Test the Function

After creating the function and sequence, you should test the function to confirm it works as expected. Execute the following query to generate a new ID:

```sql
SELECT generate_object_id();
```

This query should return a unique 12-byte hexadecimal string that serves as the custom ID.

### Using the Custom ID in PostgreSQL Tables and Applications

The custom ID generation function is a powerful feature that allows for the creation of unique identifiers for records in a PostgreSQL database. This section delves into the technical details of using this function in PostgreSQL tables, inserting data with automatically generated IDs, and integrating this functionality into applications.

#### Table Creation with Custom ID

When creating a new table that requires a unique identifier for each record, the custom ID can be set as the primary key. Here's an example of how to define a table with a custom ID as the primary key:

```sql
CREATE TABLE vouchers (
  id bytea PRIMARY KEY DEFAULT generate_custom_id(),
  name text NOT NULL,
  description text,
  value numeric
);
```

This SQL statement creates a table named `vouchers` with four columns. The `id` column uses the `bytea` data type suitable for storing binary strings and is set as the primary key. The `DEFAULT generate_custom_id()` clause ensures that every new record will have a unique ID generated by the `generate_custom_id()` function.

#### Inserting Data with Custom ID

Inserting data into the table is straightforward. The custom ID function will automatically generate a unique identifier for each new record. Here's how you can insert data without specifying the `id` column:

```sql
INSERT INTO vouchers (name, description, value)
VALUES ('Summer Sale', '20% discount on all products', 20);
```

In this `INSERT` statement, only the `name`, `description`, and `value` columns are specified. The `id` column is omitted, allowing the database to fill it with a custom-generated ID.

#### Application Integration

Integrating the custom ID functionality into applications involves a few key steps:

1. **Establish a Database Connection**: Use the appropriate database driver to establish a connection to your PostgreSQL database from within your application.

2. **Prepare the Query**: Formulate SQL queries to insert new records or retrieve existing ones. Ensure that the custom ID is used as the primary key where necessary.

3. **Execute the Query**: Run the SQL query through your application and manage the results, whether it's inserting new data or fetching existing records.

By implementing these steps, developers can effectively utilize the custom ID feature in their PostgreSQL databases and associated applications.



### Considerations and Limitations

When integrating a custom ID generation function to simulate MongoDB's ObjectID in PostgreSQL, it's imperative to thoroughly assess its potential impact on system performance, ensure the robustness of its uniqueness guarantees, and understand its inherent limitations.

#### Performance 

The custom ID generation function, while offering a unique solution, may incur performance penalties, especially under high-load conditions. Unlike native integer-based keys, this function performs additional computations to generate a unique identifier, which can introduce latency and processing overhead. Continuous monitoring and performance tuning are essential to ensure that the function does not become a bottleneck in the system.

#### Uniqueness Concerns

The function's design incorporates a timestamp, machine identifier, process identifier, and a random counter to produce a unique ID. However, in environments with distributed architectures or where concurrent processes are prevalent, the risk of ID collisions cannot be ignored. Rigorous testing must be conducted to validate the function's ability to maintain uniqueness across various scenarios and workloads.

#### Limitations and Compatibility Issues

As a user-defined function within PostgreSQL, the custom ID generation function may face compatibility challenges with other databases or applications that have specific expectations for primary key formats. Furthermore, PostgreSQL's configuration—such as how sequences are cached or the transaction isolation level—can influence the function's behavior, leading to unexpected results.

### Future Work

The groundwork laid by this blog post paves the way for further investigative and developmental pursuits. The following areas present opportunities for continued enhancement and research:

- **Performance Optimization**: Delving deeper into the performance aspect, future iterations could focus on optimizing the ID generation function. This entails identifying bottlenecks and implementing strategies to minimize latency, particularly in scenarios with high transaction volumes.

- **Uniqueness Enhancements**: To bolster the assurance of ID uniqueness, future enhancements might incorporate advanced techniques such as distributed consensus algorithms or leveraging cryptographic methods to generate non-colliding identifiers.

- **Compatibility Extensions**: Expanding the function's utility, efforts could be directed towards creating compatibility layers. These would act as interfaces or adaptors, enabling the seamless integration of the custom ID generation function with a variety of database systems and client-side applications.

- **Benchmarking and Comparison**: A comprehensive benchmarking study is proposed to quantitatively assess the custom ID generation function. This would involve contrasting its performance and suitability against established methods like UUIDs or sequential integers, providing empirical data to inform best-practice recommendations.

The continuous evolution of the custom ID generation function promises to enhance its value as an indispensable tool for unique identifier management in PostgreSQL databases, catering to the ever-evolving landscape of data management.
