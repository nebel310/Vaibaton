#  предсказывает количество людей в коворкинге на каждый конкретный час в будущем
import pandas as pd
import numpy as np
import sqlite3
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

matplotlib.use('Agg')

# Настройка стиля графиков
plt.style.use('default')
sns.set_palette("husl")

# Подключаемся к базе данных
conn = sqlite3.connect('coworking.db')

# Загружаем данные о посещениях
query = """
SELECT 
    visit_date,
    visit_time,
    duration_minutes,
    faculty
FROM visits
"""
df = pd.read_sql_query(query, conn)

# Преобразуем дату и время в datetime
df['datetime'] = pd.to_datetime(df['visit_date'] + ' ' + df['visit_time'])

# Создаем целевую переменную - количество людей в час
df['date_hour'] = df['datetime'].dt.floor('h')
hourly_attendance = df.groupby('date_hour').size().reset_index(name='people_count')

# СОЗДАЕМ ПРИЗНАКИ ПЕРЕД ПОСТРОЕНИЕМ ГРАФИКОВ
hourly_attendance['hour'] = hourly_attendance['date_hour'].dt.hour
hourly_attendance['day_of_week'] = hourly_attendance['date_hour'].dt.dayofweek
hourly_attendance['is_weekend'] = hourly_attendance['day_of_week'].isin([5, 6]).astype(int)
hourly_attendance['month'] = hourly_attendance['date_hour'].dt.month
hourly_attendance['day_of_month'] = hourly_attendance['date_hour'].dt.day

# ГРАФИК 1: Исторические данные посещений
fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# 1.1 Общая динамика посещений по дням
daily_attendance = hourly_attendance.groupby(hourly_attendance['date_hour'].dt.date)['people_count'].sum()
axes[0, 0].plot(daily_attendance.index, daily_attendance.values)
axes[0, 0].set_title('Динамика посещений по дням')
axes[0, 0].set_xlabel('Дата')
axes[0, 0].set_ylabel('Количество посещений')
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].tick_params(axis='x', rotation=45)

# 1.2 Посещения по часам (средние)
hourly_avg = hourly_attendance.groupby('hour')['people_count'].mean()
axes[0, 1].bar(hourly_avg.index, hourly_avg.values, color='skyblue')
axes[0, 1].set_title('Средняя посещаемость по часам дня')
axes[0, 1].set_xlabel('Час дня')
axes[0, 1].set_ylabel('Среднее количество людей')
axes[0, 1].set_xticks(range(0, 24, 2))
axes[0, 1].grid(True, alpha=0.3)

# 1.3 Посещения по дням недели
daily_avg = hourly_attendance.groupby('day_of_week')['people_count'].mean()
days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
axes[1, 0].bar(days, daily_avg.values, color='lightgreen')
axes[1, 0].set_title('Средняя посещаемость по дням недели')
axes[1, 0].set_xlabel('День недели')
axes[1, 0].set_ylabel('Среднее количество людей')
axes[1, 0].grid(True, alpha=0.3)

# 1.4 Heatmap: посещаемость по дням и часам
pivot_data = hourly_attendance.pivot_table(
    values='people_count',
    index='hour',
    columns='day_of_week',
    aggfunc='mean'
)
pivot_data.columns = days
im = axes[1, 1].imshow(pivot_data.values, cmap='YlOrRd', aspect='auto')
axes[1, 1].set_title('Тепловая карта посещаемости\n(час × день недели)')
axes[1, 1].set_xlabel('День недели')
axes[1, 1].set_ylabel('Час дня')
axes[1, 1].set_xticks(range(len(days)))
axes[1, 1].set_xticklabels(days)
axes[1, 1].set_yticks(range(0, 24, 2))
plt.colorbar(im, ax=axes[1, 1])

plt.tight_layout()
plt.savefig('historical_attendance_analysis.png', dpi=300, bbox_inches='tight')
plt.close()
print("График исторических данных сохранен как 'historical_attendance_analysis.png'")


# Добавляем признаки сезонности
def get_time_of_day(hour):
    if 6 <= hour < 12:
        return 0  # утро
    elif 12 <= hour < 18:
        return 1  # день
    else:
        return 2  # вечер


hourly_attendance['time_of_day'] = hourly_attendance['hour'].apply(get_time_of_day)

# Добавляем лаговые признаки
hourly_attendance = hourly_attendance.sort_values('date_hour')
hourly_attendance['lag_24h'] = hourly_attendance['people_count'].shift(24)
hourly_attendance['lag_1h'] = hourly_attendance['people_count'].shift(1)
hourly_attendance['rolling_mean_3d'] = hourly_attendance['people_count'].shift(24).rolling(window=3).mean()

# Удаляем строки с NaN значениями
hourly_attendance = hourly_attendance.dropna()

# Подготовка данных для модели
X = hourly_attendance[['hour', 'day_of_week', 'is_weekend', 'month',
                       'time_of_day', 'lag_24h', 'lag_1h', 'rolling_mean_3d']]
y = hourly_attendance['people_count']

# Разделяем на обучающую и тестовую выборки
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=False
)

# Создаем и обучаем модель
model = xgb.XGBRegressor(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.1,
    random_state=42,
    subsample=0.8,
    colsample_bytree=0.8
)

model.fit(X_train, y_train)

# Делаем предсказания
pred = model.predict(X_test)

# Оцениваем модель
mae = mean_absolute_error(y_test, pred)
mse = mean_squared_error(y_test, pred)
rmse = np.sqrt(mse)

print(f'MAE: {mae:.2f}')
print(f'RMSE: {rmse:.2f}')

# ГРАФИК 2: Сравнение реальных и предсказанных значений
plt.figure(figsize=(15, 5))

# Берем только часть данных для наглядности
sample_size = min(100, len(y_test))
test_indices = range(sample_size)

plt.plot(test_indices, y_test.values[:sample_size], label='Реальные значения', linewidth=2, marker='o', markersize=4)
plt.plot(test_indices, pred[:sample_size], label='Предсказания', linewidth=2, linestyle='--', marker='s', markersize=4)
plt.title('Сравнение реальных и предсказанных значений посещаемости')
plt.xlabel('Индекс наблюдения')
plt.ylabel('Количество людей')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('prediction_vs_actual.png', dpi=300, bbox_inches='tight')
plt.close()
print("График сравнения предсказаний сохранен как 'prediction_vs_actual.png'")

# Сохраняем модель
joblib.dump(model, 'attendance_xgb.pkl')
print("Модель сохранена как 'attendance_xgb.pkl'")


# Функция для прогнозирования на будущее и сохранения в БД
def save_predictions_to_db(model, last_known_data, hours_to_predict=168):
    predictions = []
    current_data = last_known_data.copy()
    current_datetime = hourly_attendance['date_hour'].iloc[-1]

    # Создаем таблицу для прогнозов
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_datetime TEXT,
        predicted_attendance REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    prediction_datetimes = []
    prediction_values = []

    for i in range(hours_to_predict):
        pred_value = model.predict([current_data])[0]
        current_datetime += timedelta(hours=1)

        cursor.execute('''
        INSERT INTO predictions (prediction_datetime, predicted_attendance)
        VALUES (?, ?)
        ''', (current_datetime.strftime('%Y-%m-%d %H:%M:%S'), float(pred_value)))

        predictions.append((current_datetime, pred_value))
        prediction_datetimes.append(current_datetime)
        prediction_values.append(pred_value)

        # Обновляем данные для следующего предсказания
        current_data[0] = current_datetime.hour
        current_data[1] = current_datetime.weekday()
        current_data[2] = 1 if current_datetime.weekday() >= 5 else 0
        current_data[3] = current_datetime.month
        current_data[4] = get_time_of_day(current_data[0])
        current_data[5] = current_data[7]
        current_data[6] = pred_value
        current_data[7] = (current_data[7] + pred_value) / 2

    conn.commit()

    # ГРАФИК 3: Прогноз на будущее
    plt.figure(figsize=(15, 6))

    # Показываем только даты без времени для лучшей читаемости
    prediction_dates = [dt.strftime('%Y-%m-%d\n%H:00') for dt in prediction_datetimes]

    # Берем каждый 12-й час для подписей, чтобы не перегружать график
    xtick_indices = range(0, len(prediction_dates), 12)
    xtick_labels = [prediction_dates[i] for i in xtick_indices]

    plt.plot(range(len(prediction_values)), prediction_values,
             label='Прогноз', linewidth=2, color='red', linestyle='--')

    plt.axvline(x=0, color='gray', linestyle=':', alpha=0.7, label='Начало прогноза')
    plt.title('Прогноз посещаемости на 7 дней вперед')
    plt.xlabel('Часы прогноза')
    plt.ylabel('Количество людей')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(xtick_indices, xtick_labels, rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('future_prediction.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("График прогноза на будущее сохранен как 'future_prediction.png'")

    return predictions

# Сохраняем прогнозы на неделю вперед в БД
print("\nСохранение прогнозов в базу данных...")
last_known_row = X.iloc[-1].values
future_predictions = save_predictions_to_db(model, last_known_row, 168)

print(f"Сохранено {len(future_predictions)} прогнозов в таблицу 'predictions'")

# Показываем примеры сохраненных прогнозов
cursor = conn.cursor()
cursor.execute('SELECT * FROM predictions ORDER BY prediction_datetime LIMIT 10')
recent_predictions = cursor.fetchall()

# Закрываем соединение с БД
conn.close()

print("\nГотово!")
print("✅ Модель обучена и сохранена")
print("✅ Прогнозы сохранены в базу данных")
print("✅ Графики сохранены в файлы:")
print("   - historical_attendance_analysis.png")
print("   - prediction_vs_actual.png")
print("   - future_prediction.png")