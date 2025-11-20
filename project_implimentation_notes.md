### Low Level Design
-------------------------
* we are going to design the application using the CRDT (Conflict free replicated data type) and for the data type we are choosing the DHT (distributed Hash Table)
* There wont be any master worker architecture, its all peer to peer so every worker will become master based on the Round robin algorithm
* we will be using `HTTP3.0/QUIC` protocol for internode communication and this plays a huge role since the data transfer is done using the same.
* AWS CLI integration where we have to verify the AWS S4 signature which basically is designed to talk on HTTP1.1 and security is top notch.
* AWS CLI should upload the file to our setup where it should use the MultiPart upload and start working on this part of setup in the repository for better results
* AWS CLI download should also support range download where the nodes must gather the things related to the chunks and should be able to download them as requried.
* make sure to use the docker setup for the testing the architecture.


Task 1:
------
>>> impliment the AWS s4 signature tag and see whether you are able authenticate using the AWS CLI and able to upload the file

