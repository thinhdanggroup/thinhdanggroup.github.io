---
layout: post
title:  "The Power of Vector Database: How It Transformed My Data Projects"
author: thinhda
categories: [vector database, PineCone]
image: assets/images/vectordb/vectordb.jpeg
tags: featured
---

As a data enthusiast and a software developer, I have always been fascinated by the challenges and opportunities of working with complex and unstructured data. These are the kinds of data that include text, images, audio, video, and other forms of information that are not easily organized or analyzed by traditional databases.

I have worked on various projects that required me to process and index such data, and to find meaningful and usable information from them. For instance, I have built semantic search engines that can find relevant documents based on their topic and sentiment, recommendation systems that can suggest products or content based on user preferences and behavior, natural language processing applications that can generate coherent and accurate text based on a query or a context, and computer vision applications that can recognize faces, objects, or scenes in images or videos.

However, I have also encountered many difficulties and limitations when working with complex data. Some of the common problems that I faced were:

- How to represent complex data in a way that captures their features or attributes accurately and efficiently
- How to store and index complex data in a way that allows for fast and scalable search and retrieval
- How to query complex data in a way that finds the most similar or relevant results based on their semantic or contextual meaning
- How to update complex data in a way that reflects the changes in the source or the index without affecting the performance
- How to manage complex data in a way that ensures the quality, reliability, and security of the data and the system

I have tried various solutions and techniques to overcome these problems, such as using keywords and metadata to classify complex data, using relational or document databases to store and index complex data, using exact matches or predefined criteria to query complex data, using batch processing or incremental updates to update complex data, and using various tools and frameworks to manage complex data. However, none of these solutions were satisfactory or optimal for me. They either lacked the flexibility, accuracy, or efficiency that I needed for my projects, or they required too much effort, time, or cost to implement and maintain.

That's when I discovered the power of vector database. A vector database is a type of database that stores data as high-dimensional vectors, which are mathematical representations of features or attributes. The main advantage of a vector database is that it allows for fast and accurate similarity search and retrieval of data based on their vector distance or similarity. This means that instead of using traditional methods of querying databases based on exact matches or predefined criteria, you can use a vector database to find the most similar or relevant data based on their semantic or contextual meaning.

In this blog post, I will share with you how vector database transformed my data projects and how I use Pinecone as my vector database provider. I will also explain what vector database is, how it works, what are its benefits and drawbacks, and how you can use it for your own projects.

# What is Vector Database?

Vector database is a type of database that stores data as high-dimensional vectors. Vectors are mathematical representations of features or attributes. For example, you can represent an image as a vector of pixel values, a word as a vector of semantic values, or a product as a vector of feature values.

The main advantage of vector database is that it allows for fast and accurate similarity search and retrieval of data based on their vector distance or similarity. This means that instead of using traditional methods of querying databases based on exact matches or predefined criteria, you can use a vector database to find the most similar or relevant data based on their semantic or contextual meaning.

For example, you can use a vector database to:

- Find images that are similar to a given image based on their visual content and style
- Find documents that are similar to a given document based on their topic and sentiment
- Find products that are similar to a given product based on their features and ratings
- Find songs that are similar to a given song based on their genre and mood
- Find answers that are similar to a given question based on their relevance and correctness

To perform similarity search and retrieval in a vector database, you need to use a query vector that represents your desired information or criteria. The query vector can be either derived from the same type of data as the stored vectors (e.g., using an image as a query for an image database), or from different types of data (e.g., using text as a query for an image database). Then, you need to use a similarity measure that calculates how close or distant two vectors are in the vector space. The similarity measure can be based on various metrics, such as cosine similarity, euclidean distance, hamming distance, jaccard index. The result of the similarity search and retrieval is usually a ranked list of vectors that have the highest similarity scores with the query vector. You can then access the corresponding raw data associated with each vector from the original source or index.

The beauty of vector database is that it can handle any type of data as long as you can transform them into vectors. There are many ways to create vectors from complex data, such as using machine learning models (e.g., word embeddings), feature extraction algorithms (e.g., SIFT), transformation functions (e.g., hashing). You can also manipulate vectors in various ways to achieve different goals, such as reducing dimensions (e.g., PCA), combining vectors (e.g., concatenation), transforming vectors (e.g., normalization).

Another benefit of vector database is that it can support live index updates when you insert or delete vectors without affecting the query performance. This means that you can keep your index fresh and reflect the changes in the source data in real time. This is especially useful for applications that require timely and accurate information, such as news search, social media analysis, or e-commerce.

However, vector database is not a magic bullet that can solve all the problems of working with complex data. There are still some challenges and limitations that you need to be aware of and deal with when using vector database. Some of the common issues that you may encounter are:

- How to choose the best method to create vectors from complex data that suits your application and data type
- How to choose the best similarity measure to compare vectors that reflects your application and data type
- How to choose the best dimensionality and granularity of vectors that balances the trade-off between accuracy and efficiency
- How to choose the best vector database provider or solution that meets your performance, scalability, and cost requirements
- How to monitor, evaluate, and improve the quality and relevance of your vectors and queries

These are some of the things that you need to consider and experiment with when using vector database. There is no one-size-fits-all solution for vector database. You have to find the best combination of methods, parameters, and tools that works for your specific application and data.

# How I Use Pinecone as My Vector Database Provider

Fortunately, there are many resources and services that can help you with vector database. For example, you can use various libraries and frameworks to create and manipulate vectors, such as TensorFlow, PyTorch, Scikit-learn, Hugging Face. You can also use various services and platforms to store and index vectors, such as Pinecone, Weaviate, Milvus, Qdrant. You can also use various tools and metrics to measure and optimize vectors, such as Faiss, Annoy, NMSLIB.

I have personally used Pinecone as my vector database provider for several projects and I have been very satisfied with their service. Pinecone is a fully managed vector database that makes it easy for developers to add vector-search features to their applications, using just an API. Pinecone supports various types of data and embeddings, such as text, images, audio, video, and cross-media. Pinecone offers ultra-low query latency at any scale, even with billions of items. Pinecone allows for live index updates when you insert or delete vectors without affecting the query performance. Pinecone has a generous free tier that lets you create up to 10 indexes with up to 100K vectors each.

If you are interested in trying out Pinecone for your vector database needs, you can sign up for a free account [here](https://www.pinecone.io/). You can also check out their documentation and blog for more details and examples on how to use Pinecone for different applications and scenarios.

To give you an idea of how I use Pinecone for my projects, I will share with you one of my recent projects that involved building a semantic search engine for the Text Retrieval Conference (TREC) question classification dataset. This dataset contains 5,452 questions classified into six broad categories: abbreviation (ABBR), entity (ENTY), description (DESC), human (HUM), location (LOC), and numeric (NUM). The goal of this project was to create a vector database that can store and index the questions as vectors, and then query the database with a given question or text and get back semantically similar questions based on their category and content.

Here are the steps that I followed to complete this project:

1. Create vectors from questions: I used the OpenAI Embedding API to generate vector embeddings of the questions using their Ada 002 model. This model can produce 368-dimensional vectors from any text input. 
   
   I used the following commands to create vectors from questions:

    ```python
    from sentence_transformers import SentenceTransformer
    import torch

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
    query = 'which city is the most populated in the world?'
    xq = model.encode(query)
    ```

2. Create an index in Pinecone: I used the Pinecone Python client to create an index named "trec" that performs approximate nearest-neighbor search using the cosine similarity metric for 1536-dimensional vectors. I used the following commands to create an index in Pinecone:

    ```python
    import pinecone
    pinecone_key = os.getenv("PINECONE_KEY")
    pinecone_env = os.getenv("PINECONE_ENV")
    pinecone.init(api_key=pinecone_key, environment=pinecone_env) 
    ```

3. Insert vectors and metadata into the index: I used the upsert operation to insert the vectors and the corresponding question texts and categories into the index. I used the following commands to insert vectors and metadata into the index:

    ```python
    # Upsert sample data (5 1536-dimensional vectors with question texts and categories)
    data = [
        {"text": "What is the capital of France?", "category": "LOC"},
        {"text": "Who wrote Hamlet?", "category": "HUM"},
        {"text": "How many planets are there in the solar system?", "category": "NUM"},
        {"text": "What does AIDS stand for?", "category": "ABBR"},
        {"text": "What is the largest animal in the world?", "category": "ENTY"}
    ]

    i = 0
    vectors = []
    for v in data:
        i+=1
        xq = model.encode(v["text"])
        vectors.append(("Q"+ str(i), xq.tolist(), v))
    index = pinecone.Index('test')

    index.upsert(
        vectors=vectors,
    )
    ```

4. Query the index and get similar vectors: I used the query operation to query the index with a given question or text and get back semantically similar questions based on their vector similarity. I used the following commands to query the index and get similar vectors:

    ```python
    question = "What is the name of Shakespeare's wife?"
    xq =  model.encode(question).tolist()
    res = index.query(xq, top_k=3,  include_metadata=True)

    # Print results
    for result in res['matches']:
        print(f"{round(result['score'], 2)}: {result['metadata']['text']} - category {result['metadata']['category']}")
    ```

    The output of the query operation should look something like this:

    ```md
    0.56: Who wrote Hamlet? - category HUM
    0.24: What is the capital of France? - category LOC
    0.18: What does AIDS stand for? - category ABBR
    ```

    As you can see, the query operation returns a ranked list of questions that have the highest vector similarity with the query question based on their category and content.

5. Delete the index: I used the delete operation to delete the index when I was done with it. I used the following commands to delete the index:

    ```python
    # Delete index
    pinecone.delete_index('test')
    ```

This was one of my projects that involved using vector database with Pinecone and OpenAI for semantic search and retrieval of questions. I was very impressed by how easy and fast it was to create and use a vector database with Pinecone and OpenAI, and how accurate and relevant the results were.

# Conclusion

In this blog post, I shared my experience of working with complex data and how I discovered the power of vector database and how it transformed my data projects. I also introduced Pinecone as a fully managed vector database service that I use for my projects.

Vector database is a powerful tool for working with complex data that enables fast and accurate similarity search and retrieval based on semantic or contextual meaning. Vector database can handle any type of data as long as you can transform them into vectors. Vector database can support live index updates without affecting the query performance.

However, vector database also has some challenges and limitations that you need to be aware of and deal with when using it. You have to find the best combination of methods, parameters, and tools that works for your specific application and data.

I hope this blog post has given you some insights into what vector database is and why you need one. If you have any questions or comments about vector database or Pinecone, feel free to leave them below or contact me directly. I would love to hear from you.

<!-- In this blog post, I share my experience of working with complex data and how I discovered the power of vector database and how it transformed my data projects. I also introduce Pinecone as a fully managed vector database service that I use for my projects. -->