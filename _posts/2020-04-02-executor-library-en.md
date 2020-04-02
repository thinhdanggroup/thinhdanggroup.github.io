---
layout: post
title:  "Executor: Worker Pool in Golang"
author: thinhda
categories: [ golang , reflect, workerPool]
image: assets/images/executor/banner.jpeg
tags: featured
---

The purpose of creating this library is because golang's existing libraries have not yet features such as flexibility with the definition of job running, limiting the number of jobs executed over a period of time. In the past, I created and repeated the code based on the idea of the Worker Pool and know the trouble when reimplemented but never generalized to create a complete library. In the end, I stopped and created Executor.

# Overview

[Executor](https://github.com/thinhdanggroup/executor) is a simple Worker Pool library with features:

- Job has an implementation function with a variety of params passed by reflection
- Worker created by Goroutine
- A "rate limter" to support jobs like crawl data, loadtest, ...

# How It Works

The principle is quite simple:

![grpc-web-model](/assets/images/executor/executor.png)

The Executor will push Jobs into a Channel. The Channel will mediate to transfer Jobs to the Workers and also make sure the Workers are not overloaded.

The most interesting part is still how to generalize Jobs. Now that I have started to learn about golang's "reflect", I have seen that we can implement a function with just the *interface* provided, function "Call" will do it. But what about the input parameters. At this time, *Variadic Functions* promote its advantages. And finally, I just need to validate the information of the input:

```golang
func validateFunc(handler interface{}, nArgs int) (interface{}, error) {
  method := reflect.ValueOf(handler)
	f := reflect.Indirect(method)

  // check type func
	if f.Kind() != reflect.Func {
		return f, fmt.Errorf("%T must be a Function ", f)
	}

	methodType := method.Type()
	numIn := methodType.NumIn()

  // check number of args 
	if nArgs < numIn {
		return nil, errors.New("Call with too few input arguments")
	} else if nArgs > numIn {
		return nil, errors.New("Call with too many input arguments")
	}
	return f, nil
}
```

# Example

Config:

```golang
type Config struct {
	ReqPerSeconds int
	QueueSize     int
	NumWorkers    int
}
```

Executor will use 3 basic parameters:

- ReqPerSeconds: limit the number of jobs per second. if it is 0, the executor will be no limit.
- QueueSize: buffer size of the channel.
- NumWorkers: the number of workers executing.

```golang

func main() {
	executor, err := executor.New(executor.DefaultConfig())

	if err != nil {
		logrus.Error(err)
	}

	// close resource before quit
	defer executor.Close()

	for i := 0; i < 3; i++ {
		executor.Publish(mul, i)
		executor.Publish(pow, i)
		executor.Publish(sum, i, i+1)
	}

}

func mul(input int) {
	fmt.Printf("2 * %d = %d \n", input, 2*input)
}

func pow(input int) {
	fmt.Printf("2 ^ %d = %d \n", input, input^2)
}

func sum(a int, b int) {
	fmt.Printf("%d + %d = %d \n", a, b, a+b)
}

// Output:
// 2 * 0 = 0 
// 2 ^ 0 = 2 
// 2 ^ 1 = 3 
// 1 + 2 = 3 
// 2 * 2 = 4 
// 2 ^ 2 = 0 
// 2 + 3 = 5 
// 0 + 1 = 1 
// 2 * 1 = 2

```

After initializing the Executor, remember the Close resource. Inside the Close function, the library will wait for the Job to complete and then close the Channel.

As you can see, we just have to execute the function and the parameter, the worker will do the rest for us. Too simple is not it!

