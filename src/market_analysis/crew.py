# src/data_collection/crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from .tools.youtube_collection_tool import YouTubeCollectionTool
from .tools.config_loader_tool import ConfigLoaderTool
from .tools.data_processor_tool import DataProcessorTool

@CrewBase
class DataCollectionCrew():
    """DataCollection crew for multi-platform content gathering"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def channel_manager(self) -> Agent:
        return Agent(
            config=self.agents_config['channel_manager'],
            verbose=True,
            tools=[ConfigLoaderTool()]
        )

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

    @task
    def load_configuration_task(self) -> Task:
        return Task(
            config=self.tasks_config['load_configuration_task']
        )

    @task
    def youtube_collection_task(self) -> Task:
        return Task(
            config=self.tasks_config['youtube_collection_task']
        )

    @task
    def data_processing_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_processing_task'],
            output_file='output/collected_data.json'
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