# Google sign-in setup (one time, for all devices)

Every calendar uses the same Google "OAuth client". It identifies *your product* to Google.
Each customer still signs in with their own account and gives read-only access to their calendar.

## Why not "enter a code on google.com/device"?

Google's TV-style sign-in doesn't allow Calendar access. Instead:

```
phone ──► calendar web page ──► Google sign-in ──► relay page (HTTPS, static)
                                                      │ sends the same phone browser back to
                                                      ▼
                                   http://192.168.x.y/oauth/callback ──► calendar stores the sign-in
```

The relay page (`relay/index.html`) is a 60-line static file. It sees only a one-time code that is
useless without the secret stored on the device, and it never stores or sends anything.
Later, a cloud pairing service can replace it without changing the device much.

## Steps

### 1. Host the relay page (GitHub Pages, free)

1. On github.com create a **public** repository, e.g. `inkcal-relay`.
2. Upload `relay/index.html` from this project to the root of that repository.
3. Repository → Settings → Pages → *Deploy from a branch* → `main` / root → Save.
4. After a minute it is live at `https://<your-github-user>.github.io/inkcal-relay/`.
   Note this URL **with the trailing slash**.

### 2. Google Cloud project

You can reuse the project from the old `raspberry-calendar` attempt, or create a new one:

1. https://console.cloud.google.com → project picker → **New project** → "E-ink Calendar".
2. *APIs & Services → Library* → search **Google Calendar API** → **Enable**.
3. *Google Auth Platform* (OAuth consent screen):
   - **Branding**: app name (what customers see, e.g. "E-ink Calendar"), support email.
   - **Audience**: *External*. While testing, add your Gmail address (and anyone else's) under **Test users**.
   - **Data access** → Add scopes: `.../auth/calendar.readonly`, `openid`, `.../auth/userinfo.email`.
4. *Clients* → **Create client** → type **Web application**:
   - Name: "Calendar devices"
   - **Authorized redirect URIs**: the relay URL from step 1, exactly, e.g.
     `https://<your-github-user>.github.io/inkcal-relay/`
   - Create → **Download JSON**.

   The old project's client has type "Desktop/installed". It won't work with this flow, so create the Web one.

### 3. Put the file in the project

Save the downloaded file as:

```
eink-calendar/secrets/google_client.json
```

`secrets/` is git-ignored. `deploy.sh` copies the file to `/etc/inkcal/google_client.json` on the Pi.

## Testing vs. production: important

- **Testing** status: only listed test users can sign in, **and Google expires the sign-in after
  7 days**. Fine for development; the calendar will then ask to be linked again.
- For your own home devices: set *Audience → Publish app* (**In production**). Without verification, people see
  a "Google hasn't verified this app" warning (*Advanced → Go to …*) and there is a 100-user cap,
  but sign-ins no longer expire.
- **Before selling**: Google must verify the app because `calendar.readonly` is a *sensitive* scope.
  You need your own domain (a `github.io` subdomain can't be verified), a homepage and a
  privacy policy on it, the relay page hosted on that domain, and a short demo video of the
  sign-in. Plan a few weeks for it.
