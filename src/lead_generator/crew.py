import logging
import sys
import importlib
import os
from pathlib import Path
from typing import List, Dict, Optional, Any

from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import yaml

# Function to reload this module
def reload_module():
    """Reload this module to pick up any changes."""
    module_name = __name__
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
        logging.info(f"Reloaded module: {module_name}")

# Reload this module when imported
reload_module()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

class LeadOutput(BaseModel):
    company_name: Optional[str] = Field(description="The name of the company")
    annual_revenue: Optional[str] = Field(description="Annual revenue of the company")
    location: Optional[Dict[str, str]] = Field(description="Location with city and country fields")
    website_url: Optional[str] = Field(description="Company website URL")
    review: Optional[str] = Field(description="Description of what the company does")
    num_employees: Optional[int] = Field(description="Number of employees")
    key_decision_makers: Optional[List[Dict[str, str]]] = Field(description="List of key people with their LinkedIn profiles")
    score: Optional[int] = Field(description="Fit score on a scale of 1-10")

class LeadGenerator():
    """LeadGenerator crew"""
    
    def __init__(self, serper_api_key: str = None):
        """Initialize the LeadGenerator with an optional SERPER API key.
        
        Args:
            serper_api_key (str, optional): The SERPER API key for search functionality.
        """
        # Store the API key
        self.serper_api_key = serper_api_key or os.environ.get('SERPER_API_KEY')
        
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load configurations
        agents_config_path = os.path.join(current_dir, 'config', 'agents.yaml')
        tasks_config_path = os.path.join(current_dir, 'config', 'tasks.yaml')
        
        with open(agents_config_path, 'r') as f:
            self.agents_config = yaml.safe_load(f)
        with open(tasks_config_path, 'r') as f:
            self.tasks_config = yaml.safe_load(f)
        
        # Initialize tools
        self.search_tool = None
        self.scrape_tool = None
        self._initialize_tools()
        
        # Initialize agents
        self.lead_generator = self._create_lead_generator_agent()
        self.contact_agent = self._create_contact_agent()
        self.lead_qualifier = self._create_lead_qualifier_agent()
        self.sales_manager = self._create_sales_manager_agent()
        
        # Initialize tasks
        self.lead_generation_task = self._create_lead_generation_task()
        self.contact_research_task = self._create_contact_research_task()
        self.lead_qualification_task = self._create_lead_qualification_task()
        self.sales_management_task = self._create_sales_management_task()
    
    def _initialize_tools(self):
        """Initialize the tools with the available API keys."""
        try:
            from crewai_tools import SerperDevTool, ScrapeWebsiteTool
            
            # Initialize search tool if API key is available
            if self.serper_api_key:
                try:
                    # Ensure the API key is set in the environment
                    os.environ['SERPER_API_KEY'] = self.serper_api_key
                    self.search_tool = SerperDevTool()
                    logger.info("Search tool (SerperDevTool) initialized successfully")
                except Exception as e:
                    logger.debug(f"Could not initialize search tool: {str(e)}")
                    if 'SERPER_API_KEY' in os.environ:
                        logger.warning(f"Using SERPER_API_KEY from environment: {'*' * 8 + self.serper_api_key[-4:] if self.serper_api_key else 'Not set'}")
            else:
                logger.info("SERPER_API_KEY not provided, search tool will not be available")
            
            # Initialize scrape tool
            try:
                self.scrape_tool = ScrapeWebsiteTool()
                logger.info("Scrape tool (ScrapeWebsiteTool) initialized successfully")
            except Exception as e:
                logger.debug(f"Could not initialize scrape tool: {str(e)}")
                
        except ImportError as e:
            logger.warning(f"crewai_tools not available. Some features may be limited. Error: {str(e)}")
            logger.info("You can install it with: pip install crewai-tools")
        
        # Log final tool status
        logger.info(f"Final tool status - Search Tool: {self.search_tool is not None}, Scrape Tool: {self.scrape_tool is not None}")
    
    def _create_lead_generator_agent(self) -> Agent:
        logger.info("Creating lead generator agent...")
        try:
            # Initialize tools list
            tools = []
            
            # Add available tools with logging
            if self.search_tool:
                logger.info("Adding search_tool to lead generator")
                tools.append(self.search_tool)
            else:
                logger.warning("search_tool not available for lead generator")
                
            if self.scrape_tool:
                logger.info("Adding scrape_tool to lead generator")
                tools.append(self.scrape_tool)
            else:
                logger.warning("scrape_tool not available for lead generator")
            
            logger.info(f"Lead generator will use tools: {[type(t).__name__ for t in tools]}")
            
            # Get agent config
            agent_config = self.agents_config['lead_generator']
            logger.info(f"Agent config loaded with keys: {list(agent_config.keys())}")
            
            # Create agent with tools (empty list if no tools available)
            agent = Agent(
                **agent_config,
                tools=tools,  # Always pass a list, even if empty
                verbose=True
            )
            logger.info("Lead generator agent created successfully")
            return agent
            
        except Exception as e:
            error_msg = f"Failed to create lead generator agent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    def _create_contact_agent(self) -> Agent:
        logger.info("Creating contact agent...")
        try:
            # Initialize tools list
            tools = []
            
            # Add available tools with logging
            if self.search_tool:
                logger.info("Adding search_tool to contact agent")
                tools.append(self.search_tool)
            else:
                logger.warning("search_tool not available for contact agent")
                
            if self.scrape_tool:
                logger.info("Adding scrape_tool to contact agent")
                tools.append(self.scrape_tool)
            else:
                logger.warning("scrape_tool not available for contact agent")
            
            logger.info(f"Contact agent will use tools: {[type(t).__name__ for t in tools]}")
            
            # Create agent with tools (empty list if no tools available)
            return Agent(
                **self.agents_config['contact_agent'],
                tools=tools,  # Always pass a list, even if empty
                verbose=True
            )
        except Exception as e:
            error_msg = f"Failed to create contact agent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _create_lead_qualifier_agent(self) -> Agent:
        logger.info("Creating lead qualifier agent...")
        try:
            # Initialize tools list
            tools = []
            
            # Only search_tool is used for this agent
            if self.search_tool:
                logger.info("Adding search_tool to lead qualifier")
                tools.append(self.search_tool)
            else:
                logger.warning("search_tool not available for lead qualifier")
            
            logger.info(f"Lead qualifier will use tools: {[type(t).__name__ for t in tools]}")
            
            # Create agent with tools (empty list if no tools available)
            return Agent(
                **self.agents_config['lead_qualifier'],
                tools=tools,  # Always pass a list, even if empty
                verbose=True
            )
        except Exception as e:
            error_msg = f"Failed to create lead qualifier agent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _create_sales_manager_agent(self) -> Agent:
        logger.info("Creating sales manager agent...")
        try:
            # Sales manager doesn't need any tools
            logger.info("Sales manager agent doesn't require any tools")
            
            # Create agent with empty tools list
            return Agent(
                **self.agents_config['sales_manager'],
                tools=[],  # Explicitly set to empty list
                verbose=True
            )
        except Exception as e:
            error_msg = f"Failed to create sales manager agent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _create_lead_generation_task(self) -> Task:
        task_config = self.tasks_config['lead_generation_task'].copy()
        # Remove agent from config since we'll set it directly
        task_config.pop('agent', None)
        return Task(
            **task_config,
            agent=self.lead_generator
        )

    def _create_contact_research_task(self) -> Task:
        task_config = self.tasks_config['contact_research_task'].copy()
        # Remove agent from config since we'll set it directly
        task_config.pop('agent', None)
        return Task(
            **task_config,
            agent=self.contact_agent,
            context=[self.lead_generation_task]
        )
    
    def _create_lead_qualification_task(self) -> Task:
        task_config = self.tasks_config['lead_qualification_task'].copy()
        # Remove agent from config since we'll set it directly
        task_config.pop('agent', None)
        return Task(
            **task_config,
            agent=self.lead_qualifier,
            context=[self.lead_generation_task, self.contact_research_task]
        )

    def _create_sales_management_task(self) -> Task:
        task_config = self.tasks_config.get('sales_management_task', {}).copy()
        # Remove agent from config since we'll set it directly
        task_config.pop('agent', None)
        return Task(
            **task_config,
            agent=self.sales_manager,
            context=[self.lead_qualification_task]
        )

    def crew(self) -> Crew:
        """Creates the LeadGenerator crew"""
        logger.info("Creating Crew...")
        try:
            # Create and return a new Crew instance with all agents and tasks
            return Crew(
                agents=[
                    self.lead_generator,
                    self.contact_agent,
                    self.lead_qualifier,
                    self.sales_manager
                ],
                tasks=[
                    self.lead_generation_task,
                    self.contact_research_task,
                    self.lead_qualification_task,
                    self.sales_management_task
                ],
                verbose=True,
                #planning=True,
                #memory=True,
                usage_metrics={}
            )
        except Exception as e:
            logger.error(f"Error creating crew: {str(e)}", exc_info=True)
            raise
