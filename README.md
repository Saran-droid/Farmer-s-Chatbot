# Farmer's AI Chatbot
##Link :https://saran-droid.github.io/Farmer-s-Chatbot/

## Overview

Farmer's AI Chatbot is an intelligent virtual assistant designed to help farmers with real-time agricultural information. The chatbot provides guidance on market prices, pest control, fertilizer recommendations, and general farming queries. It uses AI-powered query classification and natural language processing to deliver relevant and accurate responses.

## Features

* **Real-time Market Prices**: Fetches the latest market prices for crops based on the user’s location.
* **Pest Control Assistance**: Recommends pesticides and provides solutions for plant diseases and infections.
* **Fertilizer Recommendations**: Suggests fertilizers based on crop type.
* **General Farming Information**: Answers various farming-related questions using AI.
* **Multilingual Support**: Supports multiple languages for ease of use.
* **Speech Recognition**: Allows users to interact via voice commands.
* **Interactive UI**: Simple and user-friendly interface for seamless interaction.

## Technologies Used

* **Backend**: Flask, OpenRouter API, LangChain, Pandas
* **Frontend**: HTML, CSS, JavaScript
* **APIs & Libraries**: Flask-CORS, Requests, Speech Recognition

## Setup Instructions

### Prerequisites

* Python 3.x installed
* Node.js (for frontend testing if needed)
* Flask & dependencies

### Installation Steps

1. Clone the repository:

   ```sh
   git clone https://github.com/your-repo/farmers-chatbot.git
   cd farmers-chatbot
   ```
2. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```
3. Run the Flask server:

   ```sh
   python chatbot.py
   ```
4. Open `index.html` in a browser to access the chatbot.

## API Endpoints

* `POST /chat` - Processes user queries and returns responses.

## Usage

* Select a language from the available options.
* Type or use voice commands to ask farming-related questions.
* Receive AI-generated responses in real-time.

## Future Enhancements

* **Weather-based Recommendations**: Provide suggestions based on real-time weather data.
* **Crop Disease Detection**: Integrate AI-based image recognition for plant disease identification.
* **Mobile App Integration**: Expand chatbot functionality to mobile platforms.

## Contributors

* **Saranragav J U** (Backend)
* **Muthukumaran K** (Backend)
* **Ajay Kumar T** (Frontend)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

