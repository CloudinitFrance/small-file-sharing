# SmallFileSharing

Small File Sharing is a demo on how to share files using a REST API based on AWS API Gateway, secured by AWS Cognito and using AWS S3 for files storage.

## Pre-requisites

This demo needs to be used with:

- [CognitoApi](https://github.com/CloudinitFrance/cognito-api/): An authentication API based on AWS Cognito.


## Installation

> **Warning**
First you need to install **CognitoApi** by follwing the [installation guide](https://github.com/CloudinitFrance/cognito-api#installation).

And then you can create the following AWS resources:

- Create an S3 bucket to store the files. Let's give it a name: **thecadors-file-sharing-dev**.

- Create a DynamoDB table named: **thecadors-files** with a **Partition key** named: **file_id**. This table will keep track of all the user files. 

- Create a lambda named **upload-file** and use the code provided inside this reposirory, set the timeout for this lambda to 30 seconds and associate to it a PowerUserAccess role. Set the environement variables specified inside the file **env_vars.txt**

- Create a lambda named **get-user-files** and use the code provided inside this reposirory, set the timeout for this lambda to 30 seconds and associate to it a PowerUserAccess role. Set the environement variables specified inside the file **env_vars.txt**

- Create a lambda named **delete-user-file** and use the code provided inside this reposirory, set the timeout for this lambda to 30 seconds and associate to it a PowerUserAccess role. Set the environement variables specified inside the file **env_vars.txt**

- Create a lambda named **share-file** and use the code provided inside this reposirory, set the timeout for this lambda to 30 seconds and associate to it a PowerUserAccess role. Set the environement variables specified inside the file **env_vars.txt**

- Associate with all the created lambdas 2 AWS Lambda layers coming from the deployment of the CognitoApi project which are: **pyjwt** and **jsonschema**.

- Create a resource named **files** inside the API Gateway deployed by the **CognitoApi** project under the path: **/users/{user_id}/**, so the path of this resource will be: **/users/{user_id}/files**.

- Create a **GET** method under the resource **/users/{user_id}/files** and use **Use Lambda Proxy integration** as an integration with lambda **get-user-files**. Use as an authorization the authorizer deployed by the **CognitoApi** project and set **API Key Required** to true.

- Create a **POST** method under the resource **/users/{user_id}/files** and use **Use Lambda Proxy integration** as an integration with lambda **upload-file**. Use as an authorization the authorizer deployed by the **CognitoApi** project and set **API Key Required** to true.

- Create a resource named **{file_id}** inside the API Gateway deployed by the **CognitoApi** project under the path: **/users/{user_id}/files**, so the path of this resource will be: **/users/{user_id}/files/{file_id}**.

- Create a **DELETE** method under the resource **/users/{user_id}/files/{file_id}** and use **Use Lambda Proxy integration** as an integration with lambda **delete-user-file**. Use as an authorization the authorizer deployed by the **CognitoApi** project and set **API Key Required** to true.

- Create a resource named **share** inside the API Gateway deployed by the **CognitoApi** project under the path: **/users/{user_id}/files/{file_id}**, so the path of this resource will be: **/users/{user_id}/files/{file_id}/share**.

- Create a **POST** method under the resource **/users/{user_id}/files/{file_id}/share** and use **Use Lambda Proxy integration** as an integration with lambda **share-file**. Use as an authorization the authorizer deployed by the **CognitoApi** project and set **API Key Required** to true.

## API Documentation

> **Warning**
All endpoints needs the header: x-api-key which must be set by generating an API Key inside your AWS Api Gateway and associate it with your deployment stage and a usage plan.

You can find a Postman collection here: **postman/Small_File_Sharing_App.postman_collection.json**. You need to set the following variables inside Postman:

- **API_BASE_URL**: which is the dns name to use to call your auth api.

- **API_KEY**: should be the one that you will generate for your tests inside the API Gateway.

- **IdToken**: that you can get from the **CognitoApi** once connected.

Let's see how this API works:

- **Upload a new file**: Use a **POST** method on the endpoint: **v1/users/{{USER_ID}}/files** with the payload:

```json
{
    "file_data": "iVBORw0KGgoAAAANSUhEUgAAB0QAAANiCAYAAADxNXqHAAAMP2lDQ1BJQ0MgUHJvZml8Am4",
    "remote_file_name": "TheCadors.png"
}
```

> **Warning**
Note here, that **file_data** is the file data encoded in base64, the size of the file cannot exceed **10MB** because it's the limit that the AWS API Gateway can support as a payload.

And you will get an answer that looks like this:

```json
{
    "file_id": "70ffa2f2-b106-4cbc-86c6-d5bab6959dcd",
    "status": "UPLOADED"
}
```

![Upload a new file API Call](https://github.com/CloudinitFrance/small-file-sharing/blob/main/assets/UploadFile.png?raw=true)

- **List user files**: Use a **GET** method on the endpoint: **v1/users/{{USER_ID}}/files**, you will get an answer that looks like this:

```json
{
    "user_id": "a24554c4-e0d1-7099-6e19-ccf5c6ed29dd",
    "user_files": [
        {
            "file_id": "ac63e42f-b46b-4291-a690-0d1e63ece3a6",
            "file_name": "TheCadorsApi.drawio"
        },
        {
            "file_id": "70ffa2f2-b106-4cbc-86c6-d5bab6959dcd",
            "file_name": "TheCadors.png"
        }
    ]
}
```

![List User Files API Call](https://github.com/CloudinitFrance/small-file-sharing/blob/main/assets/GetUserFiles.png?raw=true)

- **Share a file**: Use a **POST** method on the endpoint: **v1/users/{{USER_ID}}/files/{{file_id}}/share** with the payload:

```json
{
    "share_with": ["tarek@cloudinit.fr", "tarek@lostinmac.com"]
}
```

And you will get an answer that looks like this:

```json
{
    "file_id": "70ffa2f2-b106-4cbc-86c6-d5bab6959dcd",
    "file_name": "TheCadors.png",
    "status": "SHARED"
}
```

After this call, all the emails with who you share the file, will receive an email containing a download link valid for 1 hour.

![Share a File API Call](https://github.com/CloudinitFrance/small-file-sharing/blob/main/assets/ShareFile.png?raw=true)
![Share a File Email Link](https://github.com/CloudinitFrance/small-file-sharing/blob/main/assets/FileSharing-Email.png?raw=true)

- **Delete a file**: Use a **DELETE** method on the endpoint: **v1/users/{{USER_ID}}/files/{{file_id}}** and you will get an answer that looks like this:

And you will get an answer that looks like this:

```json
{
    "user_id": "a24554c4-e0d1-7099-6e19-ccf5c6ed29dd",
    "file_id": "70ffa2f2-b106-4cbc-86c6-d5bab6959dcd",
    "file_name": "TheCadors.png",
    "file_status": "DELETED"
}
```

![Delete a File API Call](https://github.com/CloudinitFrance/small-file-sharing/blob/main/assets/DeleteFile.png?raw=true)

## License

[Mozilla Public License v2.0](https://github.com/CloudinitFrance/small-file-sharing/blob/main/LICENSE)
