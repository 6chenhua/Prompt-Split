"""
业务操作处理子系统 - 自动生成的代码
原始需求: 任务创建：创建新的{任务项目}；情感分析：分析{用户的情感状态}；{数据}统计：统计{任务完成情况}...
"""

import json
import os
from datetime import datetime
from textblob import TextBlob
import pandas as pd

class Task:
    def __init__(self, task_id, title, description, created_at=None, completed=False, completed_at=None):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.created_at = created_at if created_at else datetime.now().isoformat()
        self.completed = completed
        self.completed_at = completed_at
    
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at,
            'completed': self.completed,
            'completed_at': self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            task_id=data['task_id'],
            title=data['title'],
            description=data['description'],
            created_at=data.get('created_at'),
            completed=data.get('completed', False),
            completed_at=data.get('completed_at')
        )

class TaskManager:
    def __init__(self, file_path='tasks.json'):
        self.file_path = file_path
        self._initialize_file()
    
    def _initialize_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump([], f)
    
    def get_next_task_id(self):
        tasks = self.get_all_tasks()
        if not tasks:
            return 1
        return max(task.task_id for task in tasks) + 1
    
    def create_task(self, title, description):
        task_id = self.get_next_task_id()
        task = Task(task_id, title, description)
        tasks = self.get_all_tasks()
        tasks.append(task)
        
        with open(self.file_path, 'w') as f:
            json.dump([t.to_dict() for t in tasks], f, indent=2)
        
        return task
    
    def get_all_tasks(self):
        try:
            with open(self.file_path, 'r') as f:
                tasks_data = json.load(f)
            return [Task.from_dict(data) for data in tasks_data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def mark_task_completed(self, task_id):
        tasks = self.get_all_tasks()
        for task in tasks:
            if task.task_id == task_id:
                task.completed = True
                task.completed_at = datetime.now().isoformat()
                
                with open(self.file_path, 'w') as f:
                    json.dump([t.to_dict() for t in tasks], f, indent=2)
                return True
        return False

class SentimentAnalyzer:
    @staticmethod
    def analyze_sentiment(text):
        if not text:
            return {'polarity': 0, 'subjectivity': 0, 'sentiment': 'neutral'}
        
        analysis = TextBlob(text)
        polarity = analysis.sentiment.polarity
        
        if polarity > 0.1:
            sentiment = 'positive'
        elif polarity < -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'polarity': polarity,
            'subjectivity': analysis.sentiment.subjectivity,
            'sentiment': sentiment
        }

class TaskStatistics:
    def __init__(self, task_manager):
        self.task_manager = task_manager
    
    def get_basic_stats(self):
        tasks = self.task_manager.get_all_tasks()
        if not tasks:
            return {'total_tasks': 0, 'completed_tasks': 0, 'completion_rate': 0.0}
        
        total_tasks = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.completed)
        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': round(completion_rate, 2)
        }
    
    def get_detailed_stats(self):
        tasks = self.task_manager.get_all_tasks()
        if not tasks:
            return pd.DataFrame(columns=['task_id', 'title', 'created_at', 'completed', 'completed_at'])
        
        tasks_data = [task.to_dict() for task in tasks]
        df = pd.DataFrame(tasks_data)
        
        df['created_at'] = pd.to_datetime(df['created_at'])
        if 'completed_at' in df.columns:
            df['completed_at'] = pd.to_datetime(df['completed_at'])
        
        return df
