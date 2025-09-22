## Notes:
-----------

1. Object Defination: Object contains the Metadata + Block of Data to be stored, where metadata can hold information such as

    a. Metadata: This contains all the metadata of the object we can use while stroing the object

        * Creation-Date: creatoion date of the object this holds the date when the object storage request recieved from front end
        * Content-Length: Size of the object in KiloBytes.
        * Content-Type: we can use the [IANA types](https://www.iana.org/assignments/media-types/media-types.xhtml) for now, but need to see if we are able to extract we are good, else we can assign some default.
        * Last-Modified: Can either hold the object creation date, or if the master server reties the object creation will be actually use this to store the object.

    eg:
    ```{json}
        {
            "Creation-Date": "2025-01-01T00:00:000000Z", 
            "Content-Length": 500,
            "Content-Type": "application/json",
            "Last-Modified": "2025-01-01T00:00:000000Z"
        }
    ```

    b. RPC network - we are going use the GRPC framework here and we here is the link to the github with examples [Github Link](https://github.com/grpc/grpc) and the documentation link for the gRPC website with python guide is [Python Guide](https://grpc.io/docs/languages/python/quickstart/)

    