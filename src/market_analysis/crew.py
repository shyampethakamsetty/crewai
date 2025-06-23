# src/data_collection/crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from .tools.youtube_collection_tool import YouTubeCollectionTool
from .tools.data_processor_tool import DataProcessorTool
from .tools.sentence_processor_tool import SentenceProcessorTool
from .tools.ticker_tagger_tool import TickerTaggerTool

@CrewBase
class DataCollectionCrew():
    """DataCollection crew for multi-platform content gathering"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def youtube_collector(self) -> Agent:
        return Agent(
            config=self.agents_config['youtube_collector'],
            verbose=True,
            tools=[YouTubeCollectionTool()]
        )

    @agent
    def data_processor(self) -> Agent:
        return Agent(
            config=self.agents_config['data_processor'],
            verbose=True,
            tools=[DataProcessorTool()]
        )

    @agent
    def sentence_processor(self) -> Agent:
        return Agent(
            config=self.agents_config['sentence_processor'],
            verbose=True,
            tools=[SentenceProcessorTool()]
        )

    @agent
    def ticker_tagger(self) -> Agent:
        return Agent(
            config=self.agents_config['ticker_tagger'],
            verbose=True,
            tools=[TickerTaggerTool()]
        )

    @task
    def youtube_collection_task(self) -> Task:
        return Task(
            config=self.tasks_config['youtube_collection_task']
        )

    @task
    def data_processing_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_processing_task']
        )

    @task
    def sentence_processing_task(self) -> Task:
        return Task(
            config=self.tasks_config['sentence_processing_task']
        )

    @task
    def ticker_tagging_task(self) -> Task:
        return Task(
            config=self.tasks_config['ticker_tagging_task']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the DataCollection crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )