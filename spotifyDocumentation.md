#Available endpoints:
Get Album
Get Several Albums
Get Album Tracks
Get User's Saved Albums
Save Albums for Current User
Remove Users' Saved Albums
Check User's Saved Albums
Get New Releases


 Get Artist
Get Several Artists
Get Artist's Albums
Get Artist's Top Tracks
Get Artist's Related Artists

Get Playback State
Transfer Playback
Get Available Devices
Get Currently Playing Track
Start/Resume Playback
Pause Playback
Skip To Next
Skip To Previous
Seek To Position
Set Repeat Mode
Set Playback Volume
Toggle Playback Shuffle
Get Recently Played Tracks
Get the User's Queue
Add Item to Playback Queue

Get Playlist
Change Playlist Details
Get Playlist Items
Update Playlist Items
Add Items to Playlist
Remove Playlist Items
Get Current User's Playlists
Get User's Playlists
Create Playlist
Get Featured Playlists
Get Category's Playlists
Get Playlist Cover Image
Add Custom Playlist Cover Image

Search for Item

Get Track
Get Several Tracks
Get User's Saved Tracks
Save Tracks for Current User
Remove User's Saved Tracks
Check User's Saved Tracks

THESE ENDPOINTS DO NOT WORK DO NOT USE THEM:
Get Several Tracks' Audio Features
Get Track's Audio Features
Get Track's Audio Analysis
Get Recommendations:
Get Recommendations

OAuth 2.0
Deprecated
Recommendations are generated based on the available information for a given seed entity and matched against similar artists and tracks. If there is sufficient information about the provided seeds, a list of tracks will be returned together with pool size details.

For artists and tracks that are very new or obscure there might not be enough data to generate a list of tracks.

Important policy note
Spotify content may not be used to train machine learning or AI model
Request

GET
/recommendations
limit
integer
The target size of the list of recommended tracks. For seeds with unusually small pools or when highly restrictive filtering is applied, it may be impossible to generate the requested number of recommended tracks. Debugging information for such cases is available in the response. Default: 20. Minimum: 1. Maximum: 100.

Default: limit=20
Range: 1 - 100
Example: limit=10
market
string
An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that is available in that market will be returned.
If a valid user access token is specified in the request header, the country associated with the user account will take priority over this parameter.
Note: If neither market or user country are provided, the content is considered unavailable for the client.
Users can view the country that is associated with their account in the account settings.

Example: market=ES
seed_artists
string
Required
A comma separated list of Spotify IDs for seed artists. Up to 5 seed values may be provided in any combination of seed_artists, seed_tracks and seed_genres.
Note: only required if seed_genres and seed_tracks are not set.

Example: seed_artists=4NHQUGzhtTLFvgF5SZesLK
seed_genres
string
Required
A comma separated list of any genres in the set of available genre seeds. Up to 5 seed values may be provided in any combination of seed_artists, seed_tracks and seed_genres.
Note: only required if seed_artists and seed_tracks are not set.

Example: seed_genres=classical,country
seed_tracks
string
Required
A comma separated list of Spotify IDs for a seed track. Up to 5 seed values may be provided in any combination of seed_artists, seed_tracks and seed_genres.
Note: only required if seed_artists and seed_genres are not set.

Example: seed_tracks=0c6xIDDpzE81m2q797ordA
min_acousticness
number
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 1
max_acousticness
number
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 1
target_acousticness
number
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 1
min_danceability
number
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 1
max_danceability
number
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 1
target_danceability
number
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 1
min_duration_ms
integer
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

max_duration_ms
integer
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

target_duration_ms
integer
Target duration of the track (ms)

min_energy
number
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 1
max_energy
number
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 1
target_energy
number
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 1
min_instrumentalness
number
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 1
max_instrumentalness
number
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 1
target_instrumentalness
number
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 1
min_key
integer
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 11
max_key
integer
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 11
target_key
integer
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 11
min_liveness
number
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 1
max_liveness
number
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 1
target_liveness
number
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 1
min_loudness
number
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

max_loudness
number
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

target_loudness
number
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

min_mode
integer
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 1
max_mode
integer
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 1
target_mode
integer
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 1
min_popularity
integer
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 100
max_popularity
integer
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 100
target_popularity
integer
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 100
min_speechiness
number
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 1
max_speechiness
number
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 1
target_speechiness
number
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 1
min_tempo
number
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

max_tempo
number
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

target_tempo
number
Target tempo (BPM)

min_time_signature
integer
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Maximum value: 11
max_time_signature
integer
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

target_time_signature
integer
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

min_valence
number
For each tunable track attribute, a hard floor on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, min_tempo=140 would restrict results to only those tracks with a tempo of greater than 140 beats per minute.

Range: 0 - 1
max_valence
number
For each tunable track attribute, a hard ceiling on the selected track attribute’s value can be provided. See tunable track attributes below for the list of available options. For example, max_instrumentalness=0.35 would filter out most tracks that are likely to be instrumental.

Range: 0 - 1
target_valence
number
For each of the tunable track attributes (below) a target value may be provided. Tracks with the attribute values nearest to the target values will be preferred. For example, you might request target_energy=0.6 and target_danceability=0.8. All target values will be weighed equally in ranking results.

Range: 0 - 1
Response
200
401
403
429
A set of recommendations


seeds
array of RecommendationSeedObject
Required
An array of recommendation seed objects.

afterFilteringSize
integer
The number of tracks available after min_* and max_* filters have been applied.

afterRelinkingSize
integer
The number of tracks available after relinking for regional availability.

href
string
A link to the full track or artist data for this seed. For tracks this will be a link to a Track Object. For artists a link to an Artist Object. For genre seeds, this value will be null.

id
string
The id used to select this seed. This will be the same as the string used in the seed_artists, seed_tracks or seed_genres parameter.

initialPoolSize
integer
The number of recommended tracks available for this seed.

type
string
The entity type of this seed. One of artist, track or genre.


tracks
array of TrackObject
Required
An array of track object (simplified) ordered according to the parameters supplied.


album
object
The album on which the track appears. The album object includes a link in href to full information about the album.


artists
array of SimplifiedArtistObject
The artists who performed the track. Each artist object includes a link in href to more detailed information about the artist.

available_markets
array of strings
A list of the countries in which the track can be played, identified by their ISO 3166-1 alpha-2 code.

disc_number
integer
The disc number (usually 1 unless the album consists of more than one disc).

duration_ms
integer
The track length in milliseconds.

explicit
boolean
Whether or not the track has explicit lyrics ( true = yes it does; false = no it does not OR unknown).


external_ids
object
Known external IDs for the track.


external_urls
object
Known external URLs for this track.

href
string
A link to the Web API endpoint providing full details of the track.

id
string
The Spotify ID for the track.

is_playable
boolean
Part of the response when Track Relinking is applied. If true, the track is playable in the given market. Otherwise false.


linked_from
object
Part of the response when Track Relinking is applied, and the requested track has been replaced with different track. The track in the linked_from object contains information about the originally requested track.


restrictions
object
Included in the response when a content restriction is applied.

name
string
The name of the track.

popularity
integer
The popularity of the track. The value will be between 0 and 100, with 100 being the most popular.
The popularity of a track is a value between 0 and 100, with 100 being the most popular. The popularity is calculated by algorithm and is based, in the most part, on the total number of plays the track has had and how recent those plays are.
Generally speaking, songs that are being played a lot now will have a higher popularity than songs that were played a lot in the past. Duplicate tracks (e.g. the same track from a single and an album) are rated independently. Artist and album popularity is derived mathematically from track popularity. Note: the popularity value may lag actual popularity by a few days: the value is not updated in real time.

preview_url
string
Nullable
Deprecated
A link to a 30 second preview (MP3 format) of the track. Can be null

Important policy note
Spotify Audio preview clips can not be a standalone service
track_number
integer
The number of the track. If an album has several discs, the track number is the number on the specified disc.

type
string
The object type: "track".

Allowed values: "track"
uri
string
The Spotify URI for the track.

is_local
boolean
Whether or not the track is from a local file.



Get Available Genre Seeds


Get Current User's Profile
Get User's Top Items
Get User's Profile
Follow Playlist
Unfollow Playlist
Get Followed Artists
Follow Artists or Users
Unfollow Artists or Users
Check If User Follows Artists or Users
Check if Current User Follows Playlist

#Display your Spotify profile data in a web app

This guide creates a simple client-side application that uses the Spotify Web API to get user profile data. We'll show both TypeScript and JavaScript code snippets, make sure to use the code that is correct for your application.

External applications can use the Spotify Web API to retrieve Spotify content, such as song data, album data and playlists. However, in order to access user-related data with the Spotify Web API, an application must be authorized by the user to access that particular information.

## Prerequisites

To work through this guide you'll need:

- A [Node.js LTS](https://nodejs.org/en/) environment or later.
- [npm](https://docs.npmjs.com/) version 7 or later
- A [Spotify account](https://accounts.spotify.com/)

## Set up your account

Login to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard). If necessary, accept the latest [Developer Terms of Service](https://developer.spotify.com/terms) to complete your account set up.

## Creating a Spotify app

We will need to register a new app to generate valid credentials - we'll use these credentials later to perform API calls. Follow the [apps guide](https://developer.spotify.com/documentation/web-api/concepts/apps) to learn how to create an app and generate the necessary credentials.

Once you've created your app, make a note of your `client_id`.

## Creating a new project

This app uses [Vite](https://vitejs.dev/) as a development server. We'll scaffold a new project with the Vite `create` command and use their default template to give us a basic app:

TypeScript

JavaScript

`   npm create vite@latest spotify-profile-demo -- --template vanilla-ts            `

Select `y` when it prompts you to install Vite.

Change directory to the new app directory that Vite just created and start the development server:

`   cd spotify-profile-demo    npm install    npm run dev            `

The default Vite template creates some files that we won't need for this demo, so you can delete all of the files in `./src/` and `./public/`

### Creating the user interface

This demo is going to be a single page application that runs entirely in the browser. We're going to replace the provided `index.html` file with a simple HTML page that constitutes the user interface to display the user's profile data.

Start by deleting the content of the `index.html` file and replacing it with a `html` and `head` tag that references a TypeScript/JavaScript file (`src/script.ts`, or `src/script.js`, we'll create this file later).

TypeScript

JavaScript

``   <!DOCTYPE html>    <html lang="en">    <head>    <meta charset="utf-8">    <title>My Spotify Profile</title>    <script src="src/script.ts" type="module"></script>    </head>    <body>        </body>    </html>        <!-- Note- We're referring directly to the TypeScript file,    and we're using the `type="module"` attribute.    Vite will transpile our TypeScript to JavaScript    so that it can run in the browser. -->            ``

Inside the `body`, we'll add some markup to display the profile data:

`   <h1>Display your Spotify profile data</h1>        <section id="profile">    <h2>Logged in as <span id="displayName"></span></h2>    <span id="avatar"></span>    <ul>    <li>User ID: <span id="id"></span></li>    <li>Email: <span id="email"></span></li>    <li>Spotify URI: <a id="uri" href="#"></a></li>    <li>Link: <a id="url" href="#"></a></li>    <li>Profile Image: <span id="imgUrl"></span></li>    </ul>    </section>            `

Some elements in this block have `id` attributes. We'll use these to replace the element's text with the data we fetch from the Web API.

### Calling the Web API

We're going to use the Web API to get the user's profile data. We'll use the [authorization code flow with PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow) to get an access token, and then use that token to call the API.

### How it works

- When the page loads, we'll check if there is a code in the callback query string
- If we don't have a code, we'll redirect the user to the Spotify authorization page.
- Once the user authorizes the application, Spotify will redirect the user back to our application, and we'll read the code from the query string.
- We will use the code to request an access token from the Spotify token API
- We'll use the access token to call the Web API to get the user's profile data.
- We'll populate the user interface with the user's profile data.

Create a `src/script.ts` or `src/script.js` file and add the following code:

TypeScript

JavaScript

`   const clientId = "your-client-id-here"; // Replace with your client id    const code = undefined;        if (!code) {    redirectToAuthCodeFlow(clientId);    } else {    const accessToken = await getAccessToken(clientId, code);    const profile = await fetchProfile(accessToken);    populateUI(profile);    }        async function redirectToAuthCodeFlow(clientId: string) {    // TODO: Redirect to Spotify authorization page    }        async function getAccessToken(clientId: string, code: string) {    // TODO: Get access token for code    }        async function fetchProfile(token: string): Promise<any> {    // TODO: Call Web API    }        function populateUI(profile: any) {    // TODO: Update UI with profile data    }            `

This is the outline of our application.

On the first line there is a `clientId` variable - you'll need to set this variable to the `client_id` of the Spotify app you created earlier.

The code now needs to be updated to redirect the user to the Spotify authorization page. To do this, let's write the `redirectToAuthCodeFlow` function:

TypeScript

JavaScript

``   export async function redirectToAuthCodeFlow(clientId: string) {    const verifier = generateCodeVerifier(128);    const challenge = await generateCodeChallenge(verifier);        localStorage.setItem("verifier", verifier);        const params = new URLSearchParams();    params.append("client_id", clientId);    params.append("response_type", "code");    params.append("redirect_uri", "http://127.0.0.1:5173/callback");    params.append("scope", "user-read-private user-read-email");    params.append("code_challenge_method", "S256");    params.append("code_challenge", challenge);        document.location = `https://accounts.spotify.com/authorize?${params.toString()}`;    }        function generateCodeVerifier(length: number) {    let text = '';    let possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';        for (let i = 0; i < length; i++) {    text += possible.charAt(Math.floor(Math.random() * possible.length));    }    return text;    }        async function generateCodeChallenge(codeVerifier: string) {    const data = new TextEncoder().encode(codeVerifier);    const digest = await window.crypto.subtle.digest('SHA-256', data);    return btoa(String.fromCharCode.apply(null, [...new Uint8Array(digest)]))    .replace(/\+/g, '-')    .replace(/\//g, '_')    .replace(/=+$/, '');    }            ``

In this function, a new `URLSearchParams` object is created, and we add the `client_id`, `response_type`, `redirect_uri` and `scope` parameters to it. The scope parameter is a [list of permissions](https://developer.spotify.com/documentation/web-api/concepts/scopes) that we're requesting from the user. In this case, we're requesting the `user-read-private` and `user-read-email` scopes - these are the scopes that allow us to fetch the user's profile data.

The `redirect_uri` parameter is the URL that Spotify will redirect the user back to after they've authorized the application. In this case, we're using a URL that points to our local Vite dev server.

_You need to make sure this URL is listed in the Redirect URIs section of your Spotify Application Settings in your Developer Dashboard._

![Edit settings to add your Redirect URI to your app](https://developer-assets.spotifycdn.com/images/documentation/web-api/add-redirect-uri.png)

You will also notice that we are generating [PKCE verifier and challenge data](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow), we're using this to verify that our request is authentic. We're using local storage to store the verifier data, which works like a password for the token exchange process.

To prevent the user from being stuck in a redirect loop when they authenticate, we need to check if the callback contains a `code` parameter. To do this, the first three lines of code in the file are modified like this:

`   const clientId = "your_client_id";    const params = new URLSearchParams(window.location.search);    const code = params.get("code");        if (!code) {    redirectToAuthCodeFlow(clientId);    } else {    const accessToken = await getAccessToken(clientId, code);    const profile = await fetchProfile(accessToken);    populateUI(profile);    }            `

In order to make sure that the token exchange works, we need to write the `getAccessToken` function.

TypeScript

JavaScript

`   export async function getAccessToken(clientId: string, code: string): Promise<string> {    const verifier = localStorage.getItem("verifier");        const params = new URLSearchParams();    params.append("client_id", clientId);    params.append("grant_type", "authorization_code");    params.append("code", code);    params.append("redirect_uri", "http://127.0.0.1:5173/callback");    params.append("code_verifier", verifier!);        const result = await fetch("https://accounts.spotify.com/api/token", {    method: "POST",    headers: { "Content-Type": "application/x-www-form-urlencoded" },    body: params    });        const { access_token } = await result.json();    return access_token;    }            `

In this function, we load the verifier from local storage and using both the code returned from the callback and the verifier to perform a POST to the Spotify token API. The API uses these two values to verify our request and it returns an access token.

Now, if we run `npm run dev`, and navigate to [http://127.0.0.1:5173](http://127.0.0.1:5173/) in a browser, we'll be redirected to the Spotify authorization page. If we authorize the application, we'll be redirected back to our application, but no data will be fetched and displayed.

To fix this, we need to update the `fetchProfile` function to call the Web API and get the profile data. Update the `fetchProfile` function:

TypeScript

JavaScript

``   async function fetchProfile(token: string): Promise<any> {    const result = await fetch("https://api.spotify.com/v1/me", {    method: "GET", headers: { Authorization: `Bearer ${token}` }    });        return await result.json();    }            ``

In this function, a call is made to `https://api.spotify.com/v1/me` using the browser's [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API) to get the profile data. The `Authorization` header is set to `Bearer ${token}`, where `token` is the access token that we got from the `https://accounts.spotify.com/api/token` endpoint.

If we add a `console.log` statement to the calling code we can see the profile data that is returned from the API in the browser's console:

`   } else {    const profile = await fetchProfile(token);    console.log(profile); // Profile data logs to console    ...    }            `

Finally, we need to update the `populateUI` function to display the profile data in the UI. To do this, we'll use the DOM to find our HTML elements and update them with the profile data:

TypeScript

JavaScript

`   function populateUI(profile: any) {    document.getElementById("displayName")!.innerText = profile.display_name;    if (profile.images[0]) {    const profileImage = new Image(200, 200);    profileImage.src = profile.images[0].url;    document.getElementById("avatar")!.appendChild(profileImage);    }    document.getElementById("id")!.innerText = profile.id;    document.getElementById("email")!.innerText = profile.email;    document.getElementById("uri")!.innerText = profile.uri;    document.getElementById("uri")!.setAttribute("href", profile.external_urls.spotify);    document.getElementById("url")!.innerText = profile.href;    document.getElementById("url")!.setAttribute("href", profile.href);    document.getElementById("imgUrl")!.innerText = profile.images[0]?.url ?? '(no profile image)';    }            `

You can now run your code by running `npm run dev` in the terminal and navigating to `http://127.0.0.1:5173` in your browser.

![Your profile data will display as a heading with your name, show your avatar image and then list your profile details](https://developer-assets.spotifycdn.com/images/documentation/web-api/profile.png)

### Adding extra type safety for TypeScript developers

At the moment, even though we're using TypeScript, we don't have any type safety around the data being returned from the Web API. To improve this, we can create a `UserProfile` interface to describes the data that we expect to be returned from the API. Adding an interface will define the shape of the object that we're expecting, this will make using the data type-safe and will allow for type prompts while coding, making a more pleasant developer experience if you extend this project in future.

To do this, create a new file called `types.d.ts` in the `src` folder and add the following code:

`   interface UserProfile {    country: string;    display_name: string;    email: string;    explicit_content: {    filter_enabled: boolean,    filter_locked: boolean    },    external_urls: { spotify: string; };    followers: { href: string; total: number; };    href: string;    id: string;    images: Image[];    product: string;    type: string;    uri: string;    }        interface Image {    url: string;    height: number;    width: number;    }            `

We can now update our calling code to expect these types:

`   async function fetchProfile(token: string): Promise<UserProfile> {    // ...    }        function populateUI(profile: UserProfile) {    // ...    }            `

You can view and fork the final code for this demo on GitHub: [Get User Profile Repository](https://github.com/spotify/web-api-examples/tree/master/get_user_profile).