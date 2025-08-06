# Display your Spotify profile data in a web app

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