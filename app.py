import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import aiohttp
import asyncio
from datetime import datetime
import nest_asyncio

nest_asyncio.apply()

def get_current_season():
    month = datetime.now().month
    if month in [12, 1, 2]:
        return 'winter'
    elif month in [3, 4, 5]:
        return 'spring'
    elif month in [6, 7, 8]:
        return 'summer'
    else:
        return 'fall'

async def get_current_temperature(city, api_key):
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={api_key}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data['main']['temp']
            else:
                return None

def is_temperature_normal(city, current_temp, current_season, historical_data):
    season_data = historical_data[(historical_data['city'] == city) & (historical_data['season'] == current_season)]
    if not season_data.empty:
        mean_temp = season_data['mean_temp'].values[0]
        std_temp = season_data['std_temp'].values[0]
        lower_bound = mean_temp - 2 * std_temp
        upper_bound = mean_temp + 2 * std_temp
        if lower_bound <= current_temp <= upper_bound:
            return True
        else:
            return False
    else:
        return None

st.title("Temperature Monitoring and Analysis")

uploaded_file = st.file_uploader("Upload Historical Temperature Data (CSV)", type="csv")
if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    if 'mean_temp' not in data.columns or 'std_temp' not in data.columns:
        seasonal_stats = data.groupby(['city', 'season']).agg({'temperature': ['mean', 'std']}).reset_index()
        seasonal_stats.columns = ['city', 'season', 'mean_temp', 'std_temp']
        data = data.merge(seasonal_stats, on=['city', 'season'], how='left')

    cities = data['city'].unique()
    selected_city = st.selectbox("Select City", cities)

    api_key = st.text_input("Enter OpenWeatherMap API Key")

    st.subheader("Descriptive Statistics for Historical Data")
    city_data = data[data['city'] == selected_city]
    st.write(city_data.describe())

    st.subheader("Time Series of Temperature with Anomalies")
    city_data['z_score'] = city_data.groupby('season')['temperature'].transform(lambda x: (x - x.mean()) / x.std())
    city_data['anomaly'] = np.abs(city_data['z_score']) > 2
    plt.figure(figsize=(10, 6))
    sns.lineplot(x='timestamp', y='temperature', data=city_data)
    sns.scatterplot(x='timestamp', y='temperature', hue='anomaly', data=city_data, palette='coolwarm', legend=False)
    plt.xticks(rotation=45)
    st.pyplot(plt)

    st.subheader("Seasonal Profiles")
    seasonal_data = city_data.groupby('season').agg({'temperature': ['mean', 'std']}).reset_index()
    seasonal_data.columns = ['season', 'mean_temp', 'std_temp']
    st.write(seasonal_data)

    if api_key:
        current_temp = asyncio.run(get_current_temperature(selected_city, api_key))
        if current_temp is not None:
            current_season = get_current_season()
            is_normal = is_temperature_normal(selected_city, current_temp, current_season, city_data)
            st.subheader(f"Current Temperature in {selected_city}")
            st.write(f"Current Temperature: {current_temp}°C")
            st.write(f"Is Normal for {current_season}: {is_normal}")
        else:
            st.error("Unable to retrieve current temperature. Please check your API key.")
