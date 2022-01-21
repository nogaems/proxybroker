# proxybroker
`Proxybroker` is a microservice that enables you to provide your application with proxies.

Features:
 - full CRUD support for every involved entity
 - REST-compliance
 - high performance due to utilizing the most recent frameworks and technologies
 - persistent across restarts of the service
 - self-generated documentation available in `OAS3` format with self-hosted `SwaggerUI` interface

Note that this is my attempt to solve a job application trial task, so I'm neither considering resolving issues nor adding features.

## Installation

### Docker

There's [docker-compose.yml](./docker-compose.yml) file provided, so you can use it as is.
Keep in mind that I personally haven't tested it against versions apart from these:
```
Docker version 20.10.9
docker-compose version 1.29.2
Python 3.9.9
```
### Manual

This is only suitable for development/testing purposes since among with the other security concerns, provided [.env](./.env) file and the service itself is not configured to establish secure connections to databases, there's no networking isolation, etc.

In order to run the service you'll need (versions in brackets are the ones I tested it myself against):
 - python (3.9.9)
 - mongodb (4.4.8)
 - redis (6.2.6)

After getting everything installed you have to edit several lines in [.env](./.env) file according to your local network configuration, something like that:
```
...
MONGO_URL=mongodb://127.0.0.1:27017
REDIS_URL=redis://127.0.0.1/0
...
```
Then within root project directory, run:
```
python -m venv venv
source ./venv/bin/activate
pip install -r api/requirements.txt

```
If everything went well, you'll be able to start it with:
```
uvicorn api.main:app --log-level debug
```

## Usage

First of all, take a look at [SwaggerUI](http://127.0.0.1:8080/docs) ([here](http://127.0.0.1:8000/docs) in case of manual deployment). It's pretty self-describing and you can even test it out and make some requests from built-in interface.
Here's a brief description of basic workflow with the service (I use `httpie` for verbosity):
```bash
# get full list of supported resources
(venv) user@desktop ~/proxybroker (main*) $ http -b :8000/resources
[
    {
        "_id": "61e9c9f8ac90e099de971d26",
        "url": "https://google.ru"
    },
    {
        "_id": "61e9c9fbac90e099de971d27",
        "url": "https://google.com"
    },
    {
        "_id": "61e9ca00ac90e099de971d28",
        "url": "https://ya.ru"
    },
    {
        "_id": "61e9ca05ac90e099de971d29",
        "url": "https://yandex.ru"
    }
]

# add a resource
(venv) user@desktop ~/proxybroker (main*) $ http -b :8000/resources url=http://some.domain/url
{
    "_id": "61e9efd55105e4e48d6c3436",
    "url": "http://some.domain/url"
}
(venv) user@desktop ~/proxybroker (main*) $ http -b :8000/resources url=http://some.domain/url
{
    "detail": "Resource with URL http://some.domain/url already exists with ID 61e9efd55105e4e48d6c3436"
}

# edit resource url
(venv) user@desktop ~/proxybroker (main*) $ http -b put :8000/resources/61e9efd55105e4e48d6c3436 url=http://some.domain/other-url
{
    "_id": "61e9efd55105e4e48d6c3436",
    "url": "http://some.domain/other-url"
}
(venv) user@desktop ~/proxybroker (main*) $ http -b put :8000/resources/61e9efd55105e4e48d6c3436 url=http://some.domain/other-url
{
    "detail": "Specified URL is the same as the former one"
}

# delete
(venv) user@desktop ~/proxybroker (main*) $ http -b delete :8000/resources/61e9efd55105e4e48d6c3436
{
    "_id": "61e9efd55105e4e48d6c3436",
    "url": "http://some.domain/other-url"
}
(venv) user@desktop ~/proxybroker (main*) $ http -b :8000/resources | grep 61e9efd55105e4e48d6c3436 | wc -l
0
```
Pretty much the same goes for proxies, again, look up schemes in the docs.

One thing I would elaborate on is the main feature itself:
```bash
# here is our setup
(venv) user@desktop ~/proxybroker (main*) $ http -b :8000/proxies
[
    {
        "_id": "61e9ca92ac90e099de971d2c",
        "country": "en",
        "resources_ids": [
            "61e9ca00ac90e099de971d28",
            "61e9ca05ac90e099de971d29"
        ],
        "url": "proxy://proxy1"
    },
    {
        "_id": "61e9ca95ac90e099de971d2d",
        "country": "ru",
        "resources_ids": [
            "61e9c9fbac90e099de971d27"
        ],
        "url": "proxy://proxy2"
    }
]

# let's try to grab a proxy
(venv) user@desktop ~/proxybroker (main*) $ http -b :8000/proxies/obtain country=ru ttl=30 resources_ids:='["61e9ca00ac90e099de971d28", "61e9ca05ac90e099de971d29"]' rpw=30
{
    "detail": "Not Found"
}

# try different country
(venv) user@desktop ~/proxybroker (main*) $ http -b :8000/proxies/obtain country=en ttl=30 resources_ids:='["61e9ca00ac90e099de971d28", "61e9ca05ac90e099de971d29"]' rpw=30
{
    "_id": "61e9ca92ac90e099de971d2c",
    "country": "en",
    "resources_ids": [
        "61e9ca00ac90e099de971d28",
        "61e9ca05ac90e099de971d29"
    ],
    "url": "proxy://proxy1"
}

# if we try to do that again
(venv) user@desktop ~/proxybroker (main*) $ http -b :8000/proxies/obtain country=en ttl=30 resources_ids:='["61e9ca00ac90e099de971d28", "61e9ca05ac90e099de971d29"]' rpw=30
{
    "detail": "Not Found"
}
# that is because it's already in use and will be automatically freed after specified 30 seconds run out

```
And last but not least, internal state of the service is stored using `Redis`, so it is both in-memory while working and automatically gets restored from disk across restarts.

## Areas of further improvements
Even though at the moment I don't feel like investing any more time in this project, here's a brief list of directions I'd go to enhance the quality of the project:
 * architecture-wise
   * add authentication mechanism along with role-based user system (this way it would be possible to split up CRUD-logic of managing resources from actually using it)
   * add SSL for reverse-proxy and an automated system to re-issue certs, etc
   * use an actual load balancer instead of default `nginx` configuration
 * code-wise
   * add fully annotated client-side library that would ease writing software utilizing this API
   * write integration/functional tests
