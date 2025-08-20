# *Spotify API ETL Pipeline: Dashboard + Real-Time React Streaming*

Introduction: After discovering the Spotify API and more specifically the recent listens endpoint of the API, I knew I wanted to store this information with a script and run analytics on it to dashboard to my personal website. I had done a bit of exploring online and could not find anything similar to gain inspiration from. So, I dove into the documentation and from there, began structuring how the project should be handled. This script will be containerized in a docker env that is hosted on my homelab.

## 1. Spotify API connection with Spotipy

The spotify API is wrapped by a library in Python called Spotipy, for readability purposes, we are going to use Spotipy to authenicate, connect, and pull data from the API. This is done with the following snippets of code:

<img width="613" height="329" alt="image" src="https://github.com/user-attachments/assets/3f897a59-4aff-4dca-bbac-efc3e9863bff" />
<br></br>

This code snippet first, loads in our secrets stored in the .ENV file, this is done to not expose my spotify API credentials while hosting this on Github. By following the .ENV.example file, it will walk you through through the items needed to generate a personal .ENV to run this script. Once that exists, the authenticate with your credentials.

## 2. Table generation and maintenance

Once authenticated with the Spotify API, we need to create/maintain the table used to store our listens to. Here is SQLite3 snippet to initiate/maintain the table:

<img width="588" height="492" alt="image" src="https://github.com/user-attachments/assets/59ee12ea-8d69-4799-8ec4-b2280e2f29a5" />
<br></br

Some design choices were taken here, but for the most part, this is essentially everything that is fed by that APIs endpoint. It is possible that there could be multiple artists that are credited on a song, in that case, we handle this by serving five columns for artists. Additionally, the start_timestamp is served in milliseconds, I am transforming this before storage into a datetime that is stored as a text.

## 3. API idle handling

To be friendly and avoid rate-limiting when there is nothing playing, I implemented some logic that will detect when nothing is playing then count the idle time to adjust the sleep timing based on the idle_count. You can see this here:

<img width="533" height="242" alt="image" src="https://github.com/user-attachments/assets/1e7bbd6b-f8aa-4edf-95c2-d66851e1707d" />
<br></br>


## 4. Grabbing the data from the API endpoint

We are now ready to assign the API endpoints to variables that we will append to a list and then using SQLite3, insert that list to the table. Here is the chunk of the script that handles assigning the API endpoints to variables that we can store:

<img width="722" height="538" alt="image" src="https://github.com/user-attachments/assets/efd31c62-a97f-498e-acbc-a2b084dd67fd" />
<br></br>

## 5. Validate and store the data to table

Once we have assigned the variables to the API endpoints, we are ready to validate that this is new data and store it to our table. The way we are handling the validation that the data is new is by checking the track_id of the last stored row. Here is the code:

<img width="949" height="757" alt="image" src="https://github.com/user-attachments/assets/7c5a502e-84a2-4615-81a8-df7be96eea95" />
<br></br>

Once the validation is checked, we are running an insert for the list of stored variables.

## 6. Exception handling 

Exception handling is basic and is still being thought through fully. Currently, if an exception is raised, it backs off for minimum 30 seconds and retrys. Here is the snippet:

<img width="654" height="299" alt="image" src="https://github.com/user-attachments/assets/1f55397e-4b18-4b19-a664-a49b8ae0c0dd" />
<br></br>



