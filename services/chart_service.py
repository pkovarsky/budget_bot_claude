import matplotlib
matplotlib.use('Agg')  # Использовать non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects
from matplotlib.patches import Wedge
import pandas as pd
import numpy as np
from io import BytesIO
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta
from database import get_db_session, User, Transaction, Category
from sqlalchemy import func

logger = logging.getLogger(__name__)

class ChartService:
    def __init__(self):
        # Настройка темной темы для красивых графиков
        plt.style.use('dark_background')
        plt.rcParams['font.size'] = 12
        plt.rcParams['figure.figsize'] = (12, 9)
        plt.rcParams['axes.facecolor'] = '#1e1e1e'
        plt.rcParams['figure.facecolor'] = '#2b2b2b'
        plt.rcParams['text.color'] = '#ffffff'
        plt.rcParams['axes.labelcolor'] = '#ffffff'
        plt.rcParams['xtick.color'] = '#ffffff'
        plt.rcParams['ytick.color'] = '#ffffff'
        plt.rcParams['axes.edgecolor'] = '#444444'
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.2
        plt.rcParams['grid.color'] = '#444444'
        plt.rcParams['axes.spines.left'] = True
        plt.rcParams['axes.spines.bottom'] = True
        plt.rcParams['axes.spines.top'] = False
        plt.rcParams['axes.spines.right'] = False
        
    def generate_category_pie_chart(self, user_id: int, period_days: int = 30) -> Optional[BytesIO]:
        """
        Генерирует круговую диаграмму расходов по категориям
        """
        db = get_db_session()
        try:
            # Получаем пользователя
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return None
            
            # Вычисляем дату начала периода
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Получаем данные о расходах по категориям
            expenses_by_category = db.query(
                Category.name,
                func.sum(func.abs(Transaction.amount)).label('total_amount')
            ).join(
                Transaction, Transaction.category_id == Category.id
            ).filter(
                Transaction.user_id == user.id,
                Transaction.amount < 0,  # Только расходы
                Transaction.created_at >= start_date
            ).group_by(Category.name).all()
            
            if not expenses_by_category:
                return None
                
            # Подготавливаем данные для диаграммы
            categories = [item[0] for item in expenses_by_category]
            amounts = [float(item[1]) for item in expenses_by_category]
            
            # Создаем красивую цветовую палитру
            colors = self._generate_colors(len(categories))
            
            # Создаем фигуру с темным фоном
            fig, ax = plt.subplots(figsize=(14, 12))
            fig.patch.set_facecolor('#2b2b2b')
            
            # Строим круговую диаграмму с тенями и улучшенным стилем
            wedges, texts, autotexts = ax.pie(
                amounts,
                labels=categories,
                colors=colors,
                autopct=lambda pct: f'{pct:.1f}%\n{self._format_amount(pct * sum(amounts) / 100)}€',
                startangle=90,
                textprops={'fontsize': 11, 'fontweight': 'bold', 'color': '#ffffff'},
                pctdistance=0.82,
                labeldistance=1.05,
                wedgeprops=dict(width=0.8, edgecolor='#2b2b2b', linewidth=2),
                shadow=True
            )
            
            # Улучшаем внешний вид процентных меток
            for autotext in autotexts:
                autotext.set_color('#000000')
                autotext.set_fontsize(10)
                autotext.set_fontweight('bold')
                autotext.set_bbox(dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
            
            # Улучшаем подписи категорий
            for text in texts:
                text.set_color('#ffffff')
                text.set_fontsize(12)
                text.set_fontweight('bold')
            
            # Добавляем стильный заголовок с датами
            total_amount = sum(amounts)
            end_date = datetime.now()
            start_date_str = start_date.strftime('%d.%m.%Y')
            end_date_str = end_date.strftime('%d.%m.%Y')
            ax.set_title(
                f'💰 Расходы по категориям\n'
                f'📅 {start_date_str} - {end_date_str} ({period_days} дней)\n'
                f'💸 Общая сумма: {self._format_amount(total_amount)}€',
                fontsize=18,
                fontweight='bold',
                color='#ffffff',
                pad=30
            )
            
            # Делаем диаграмму круглой
            ax.set_aspect('equal')
            
            # Добавляем стильную легенду
            legend_labels = [f'{cat}: {self._format_amount(amt)}€' for cat, amt in zip(categories, amounts)]
            legend = ax.legend(
                wedges,
                legend_labels,
                title="📊 Категории",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
                fontsize=11,
                title_fontsize=13,
                frameon=True,
                facecolor='#1e1e1e',
                edgecolor='#444444',
                framealpha=0.9
            )
            legend.get_title().set_color('#ffffff')
            for text in legend.get_texts():
                text.set_color('#ffffff')
            
            # Настраиваем отступы
            plt.tight_layout()
            
            # Сохраняем в буфер
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            
            plt.close()
            
            return buffer
            
        except Exception as e:
            logger.error(f"Ошибка при создании круговой диаграммы: {e}")
            return None
        finally:
            db.close()
    
    def generate_spending_trends_chart(self, user_id: int, period_days: int = 30) -> Optional[BytesIO]:
        """
        Генерирует график трендов расходов по дням
        """
        db = get_db_session()
        try:
            # Получаем пользователя
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return None
            
            # Вычисляем дату начала периода
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Получаем данные о расходах по дням
            daily_expenses = db.query(
                func.date(Transaction.created_at).label('date'),
                func.sum(func.abs(Transaction.amount)).label('total_amount')
            ).filter(
                Transaction.user_id == user.id,
                Transaction.amount < 0,  # Только расходы
                Transaction.created_at >= start_date
            ).group_by(func.date(Transaction.created_at)).all()
            
            if not daily_expenses:
                return None
            
            # Подготавливаем данные
            dates = [item[0] for item in daily_expenses]
            amounts = [float(item[1]) for item in daily_expenses]
            
            # Создаем фигуру с темным фоном
            fig, ax = plt.subplots(figsize=(16, 10))
            fig.patch.set_facecolor('#2b2b2b')
            
            # Строим красивый градиентный график
            ax.plot(dates, amounts, 
                   marker='o', linewidth=3, markersize=8, 
                   color='#00D4AA', markerfacecolor='#00FFD0', 
                   markeredgecolor='#00A67C', markeredgewidth=2,
                   linestyle='-', alpha=0.9)
            
            # Добавляем градиентную заливку
            ax.fill_between(dates, amounts, alpha=0.4, 
                           color='#00D4AA', interpolate=True)
            
            # Настраиваем оси с эмодзи
            ax.set_xlabel('📅 Дата', fontsize=14, fontweight='bold', color='#ffffff')
            ax.set_ylabel('💰 Сумма расходов (€)', fontsize=14, fontweight='bold', color='#ffffff')
            # Добавляем заголовок с датами
            end_date = datetime.now()
            start_date_str = start_date.strftime('%d.%m.%Y')
            end_date_str = end_date.strftime('%d.%m.%Y')
            ax.set_title(
                f'📈 Тренд расходов по дням\n'
                f'📅 {start_date_str} - {end_date_str} ({period_days} дней)',
                fontsize=18,
                fontweight='bold',
                color='#ffffff',
                pad=25
            )
            
            # Форматируем даты на оси x
            ax.tick_params(axis='x', rotation=45)
            
            # Добавляем сетку
            ax.grid(True, alpha=0.3)
            
            # Добавляем стильную статистику
            avg_daily = sum(amounts) / len(amounts)
            max_daily = max(amounts)
            total_amount = sum(amounts)
            
            stats_text = f'📊 Статистика:\n'
            stats_text += f'📈 Средние расходы в день: {self._format_amount(avg_daily)}€\n'
            stats_text += f'🔝 Максимум за день: {self._format_amount(max_daily)}€\n'
            stats_text += f'💸 Общая сумма: {self._format_amount(total_amount)}€'
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=12, verticalalignment='top', color='#ffffff',
                   bbox=dict(boxstyle='round,pad=0.8', facecolor='#1e1e1e', 
                           edgecolor='#00D4AA', linewidth=2, alpha=0.9))
            
            plt.tight_layout()
            
            # Сохраняем в буфер
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            
            plt.close()
            
            return buffer
            
        except Exception as e:
            logger.error(f"Ошибка при создании графика трендов: {e}")
            return None
        finally:
            db.close()
    
    def generate_monthly_comparison_chart(self, user_id: int, months: int = 6) -> Optional[BytesIO]:
        """
        Генерирует график сравнения расходов по месяцам
        """
        db = get_db_session()
        try:
            # Получаем пользователя
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return None
            
            # Получаем данные о расходах по месяцам
            monthly_expenses = db.query(
                func.strftime('%Y-%m', Transaction.created_at).label('month'),
                func.sum(func.abs(Transaction.amount)).label('total_amount')
            ).filter(
                Transaction.user_id == user.id,
                Transaction.amount < 0,  # Только расходы
                Transaction.created_at >= datetime.now() - timedelta(days=months * 30)
            ).group_by(func.strftime('%Y-%m', Transaction.created_at)).all()
            
            if not monthly_expenses:
                return None
            
            # Подготавливаем данные
            months_labels = [item[0] for item in monthly_expenses]
            amounts = [float(item[1]) for item in monthly_expenses]
            
            # Создаем фигуру с темным фоном
            fig, ax = plt.subplots(figsize=(14, 10))
            fig.patch.set_facecolor('#2b2b2b')
            
            # Создаем градиентные цвета для столбцов
            gradient_colors = self._generate_gradient_colors(len(amounts))
            
            # Строим стильную столбчатую диаграмму
            bars = ax.bar(months_labels, amounts, 
                         color=gradient_colors, alpha=0.9,
                         edgecolor='#ffffff', linewidth=1.5)
            
            # Добавляем тени к столбцам
            for bar in bars:
                bar.set_path_effects([plt.matplotlib.patheffects.SimplePatchShadow(offset=(1, -1), 
                                     shadow_rgbFace='black', alpha=0.3)])
            
            # Добавляем стильные значения на столбцы
            for bar, amount in zip(bars, amounts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max(amounts) * 0.01,
                       f'{self._format_amount(amount)}€',
                       ha='center', va='bottom', fontweight='bold', 
                       fontsize=11, color='#ffffff',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='#1e1e1e', 
                               edgecolor='#00D4AA', alpha=0.8))
            
            # Настраиваем оси с эмодзи
            ax.set_xlabel('📅 Месяц', fontsize=14, fontweight='bold', color='#ffffff')
            ax.set_ylabel('💰 Сумма расходов (€)', fontsize=14, fontweight='bold', color='#ffffff')
            ax.set_title(
                f'📊 Сравнение расходов по месяцам\n'
                f'📈 За последние {months} месяцев',
                fontsize=18,
                fontweight='bold',
                color='#ffffff',
                pad=25
            )
            
            # Поворачиваем подписи месяцев
            ax.tick_params(axis='x', rotation=45)
            
            # Добавляем сетку
            ax.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            
            # Сохраняем в буфер
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            
            plt.close()
            
            return buffer
            
        except Exception as e:
            logger.error(f"Ошибка при создании сравнительного графика: {e}")
            return None
        finally:
            db.close()
    
    def _generate_colors(self, n: int) -> List[str]:
        """
        Генерирует красивую цветовую палитру для темной темы
        """
        # Яркие неоновые цвета для темной темы
        colors = [
            '#FF6B9D', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57',
            '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43',
            '#10AC84', '#EE5A24', '#0652DD', '#9C88FF', '#FFC312',
            '#C4E538', '#12CBC4', '#FDA7DF', '#ED4C67', '#F79F1F',
            '#FF3838', '#00D4AA', '#FF6B35', '#7B68EE', '#20B2AA'
        ]
        
        if n <= len(colors):
            return colors[:n]
        else:
            # Генерируем дополнительные яркие цвета
            additional_colors = []
            for i in range(n - len(colors)):
                hue = (i * 360 / (n - len(colors))) % 360
                additional_colors.append(f'hsl({hue}, 80%, 65%)')
            return colors + additional_colors

    def _generate_gradient_colors(self, n: int) -> List[str]:
        """
        Генерирует градиентные цвета для столбчатых диаграмм
        """
        # Градиент от синего к фиолетовому к розовому
        base_colors = ['#00D4AA', '#00A8FF', '#9C88FF', '#FF6B9D', '#FF3838']
        
        if n <= len(base_colors):
            return base_colors[:n]
        
        # Интерполируем цвета для большего количества столбцов
        import numpy as np
        colors = []
        for i in range(n):
            ratio = i / (n - 1) if n > 1 else 0
            # Создаем плавный переход между цветами
            if ratio <= 0.25:
                colors.append('#00D4AA')
            elif ratio <= 0.5:
                colors.append('#00A8FF')
            elif ratio <= 0.75:
                colors.append('#9C88FF')
            else:
                colors.append('#FF6B9D')
        
        return colors
    
    def _format_amount(self, amount: float) -> str:
        """
        Форматирует сумму для отображения
        """
        if amount >= 1000:
            return f'{amount/1000:.1f}k'
        else:
            return f'{amount:.0f}'