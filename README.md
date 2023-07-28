# platform

This is the Django-based platform that powers OpenUnited. [Apps](https://docs.djangoproject.com/en/4.2/ref/applications/) are used to create separate domains:

- Product Management (Product, Capability, Initiative, Challenge, Bounty etc.)
- Talent (Person, Skill, BountyClaim etc.)
- Commerce (Organisation, Points & Payments etc.)
- Engagement (Notifications etc.)

Each app/domain has a services.py file that implements the services interface for that app/domain.

This repo contains the full platform including the frontend - which is "deliberately simple"*. We prototype and specify the target UX, as code, in the [UX Prototype repo](https://github.com/OpenUnited/ux-prototype). The UX Prototype repo is not for production use, we use it instead of using Figma.

\* Our "deliberately simple" frontend means that we use [Jinja](https://jinja.palletsprojects.com/en/3.1.x/) templates, [TailwindCSS](https://tailwindcss.com/), [TailwindUI](https://tailwindui.com/), plain javascript, and a sprinkle of [HTMX](https://htmx.org/). Earlier we had a separate ReactJS frontend and a GraphQL API layer, however [such fanciness](https://www.youtube.com/watch?v=Uo3cL4nrGOk) failed to deliver the expected value, whilst creating complexity/friction... therefore, we now have a deliberately simple frontend.

## Getting started / how to run the OpenUnited platform locally

Good if you fork this repo, then depending on your local environment, do something like the following with "OpenUnited" changed for your own GitHub username.

Database: please ensure you have postgresql running. If you haven't already, you can [download and install PostgreSQL](https://www.postgresql.org/download/) 
By default, the OpenUnited platform will look for a database named "ou_db" and use "postgres" as both the username and password. To override this, you can copy .env.example to .env locally and set the values you want.

```
git clone git@github.com:OpenUnited/platform.git
cd platform
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
python manage.py migrate
python load_sample_data.py
python manage.py runserver
```

Then navigate to: [http://localhost:8000/](http://localhost:8000/) in your browser.

Not working? Please check [the Django docs](https://docs.djangoproject.com/en/4.2/intro/tutorial01/) and make sure you have [PostgreSQL installed](https://www.google.com/search?q=how+to+install+postgresql)

