# Slack Reaction Bot 🎉✅
Allows users to see what people in a channel that have not reacted with a certain emoji on a message. It's good for using the reactions as a simply poll or something the like.

# How to use the bot 📜
In order to invoke the bot you have to start a thread on the message you want to interact with and write on of the following commands:
### Remind people of the message by @ing them in the thread:
`@<bot-name> :fire: remind here`
### Remind people by sending them a private message:
`@<bot-name> :tada: remind dm`
### Get a list of people that has not reacted with a certain emoji:
The list will be posted in the thread and only visible to the person who invoked the command.
`@<bot-name> :tada: list`

### Note
You can add how many emojis as you like to the command. The bot will only remind or list the people that has __not__ reacted with either one of the emojis you add in your command. 
# Running the application 🤖
Before we can run the application we have to create a Slack app, connect it to the backend, start the bot and then installing the Slack app onto your workspace.
## Creating the Slack App
You have to create a Slack app in order to hook this bot up to your workspace. Navigate to [api.slack.com/apps](https://api.slack.com/apps) and press "Create New App"-> "From manifest". Copy and paste the YAML configuration from the file [slack_app_manifest.yml](slack_app_manifest.yml) and then press "create app".

Next up is aquiring your `bot's slack token` and `signing secret` and add them to [.env.example](.env.example). Then, rename the file to simply `.env`. Now we can run the application. Note, if you ran `docker-compose up` before this step you have to rebuild the app since it copies all the files and creates a container upon building the application. In this case you have to rebuild the application with `docker-compose build --force`

## Starting the backend
Running the application is done easiest by using docker-compose. However, you can install everything on your machine as well and run it using python3 as well.

### Using Docker
#### Prerequisites:
* Docker
* docker-compose

To run the application using Docker and `docker-compose` you have to have them installed on your system. If you want, you can change the service- and container name in the docker-compose file.

To start the application
```sh
$ docker-compose up
```

### Using python3
### Prerequisites
* python>3.7

When standing in the root directory of this project, run the following command to install the dependencies
```sh
$ pip3 install -r requirements.txt
or, depending on your system,
$ pip install -r requirements.txt
```

## Connecting everything
After you've started the backend we have to connect the Slack application to the bot by enabling Event hooks. Open your web browser containing your Slack application services page. Navigate to "Event Subscriptions" and check the "Enable events" slider. After doing so you can paste the url to your backend in the "Request URL field". Make sure that you end the url with `/slack/events`.  
For example: `https://api.example.com/slack/events`.  
After pasting the URL into the field Slack is going to check your endpoint. You should be greeted with a green checkbox indicating that everything is as it should be. If not, check all the steps above again. Rebuidling your docker image in case you were too quick building the image the first time.

When you have created the application and started the bot's backend we can install the application to the workspace. go ahead and install it to your workspace by navigation to "Basic Information" and pressing "Install to Workspace".

# Development 🛠️
#### Prerequisites
* pipenv

If you want to continue development of this project it's recommended to do so using `pipenv`.

Install the dependencies
```sh
$ pipenv install
```

Enter the virtual environment
```sh
$ pipenv shell
```

Happy coding.

## Contributing ♻️
If you want to contribute to the project, do so by forking the repository, make your changes and then create a new PR for me to review.
Here's how you download the repo:
```sh
$ git clone git@github.com:albznw/slack-reaction-bot.git
$ cd slack-reaction-bot
```
