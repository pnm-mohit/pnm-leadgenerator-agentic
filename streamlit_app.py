# Standard library imports
import os
import sys
import importlib
import json
import logging
from datetime import datetime
from pathlib import Path

# Third-party imports
import pandas as pd
import streamlit as st

# Set page configuration - MUST be the first Streamlit command
st.set_page_config(
    page_title="AI Lead Generator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import local modules after page config
from src.components.sidebar import render_sidebar
from src.components.output_handler import capture_output
from src.lead_generator.crew import LeadGenerator
from src.utils.pricing import ModelsPricing

def clear_module_cache():
    """Clear the cache for our modules to ensure fresh imports."""
    modules_to_clear = [
        'src.lead_generator.crew',
        'src.components.sidebar',
        'src.components.output_handler',
        'src.utils.pricing'
    ]
    
    for module_name in list(sys.modules.keys()):
        if any(module_name.startswith(m) for m in modules_to_clear):
            logger.info(f"Clearing module from cache: {module_name}")
            sys.modules.pop(module_name, None)
    
    # Force reload the modules
    for module_name in modules_to_clear:
        try:
            importlib.import_module(module_name)
            logger.info(f"Reloaded module: {module_name}")
        except ImportError as e:
            logger.warning(f"Could not reload module {module_name}: {e}")

# Add Clear Cache button to sidebar
with st.sidebar:
    if st.button("🔄 Clear Caches"):
        clear_module_cache()
        st.success("Caches cleared!")
        st.rerun()

# Header with centered title
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # Center the main title using markdown with HTML
    st.markdown("<h1 style='text-align: center;'>🔍 AI Lead Generator </h1>", unsafe_allow_html=True)

# Render sidebar and get user configuration
config = render_sidebar()

# Create 3 columns with the middle one being wider
left_col, center_col, right_col = st.columns([1, 2, 1])

# Use the center column for all our content
with center_col:
    # First section: "Start Your Research" (now centered)
    st.markdown("<h2 style='text-align: center;'>Start Your Research</h2>", unsafe_allow_html=True)
    
    # Market research topic input - connected to session state
    if 'topic' not in st.session_state:
        st.session_state.topic = ""
        
    industry = st.text_input(
        "Enter a industry to research",
        placeholder="e.g., AI LLMs, Renewable Energy, FinTech",
        help="Specify the industry you want to explore for potential leads",
        key="industry"  # This links the input to st.session_state.industry
    )
    
    country = st.text_input(
        "Enter a country to research",
        placeholder="e.g., United States, United Kingdom, Canada",
        help="Specify the country you want to explore for potential leads",
        key="country"  # This links the input to st.session_state.country
    )

    # Example topics that users can click
    st.write("Or try one of these examples:")
    example_col1, example_col2, example_col3 = st.columns(3)
    
    # Define example topics
    examples = [
        "AI-powered SaaS platforms",
        "Renewable Energy Startups",
        "FinTech Payment Solutions"
    ]
    
    # Define click handler function
    def set_example_topic(example):
        st.session_state.industry = example  # Update industry instead of topic
        
    # Add a button for each example
    with example_col1:
        st.button(examples[0], on_click=set_example_topic, args=(examples[0],), key="example1")
        
    with example_col2:
        st.button(examples[1], on_click=set_example_topic, args=(examples[1],), key="example2")
        
    with example_col3:
        st.button(examples[2], on_click=set_example_topic, args=(examples[2],), key="example3")
    
    # Generate button
    run_button = st.button("🚀 Generate Leads", type="primary", use_container_width=True)
    
    # Add a small space
    st.write("")
    
    # Second section: "Why Use AI-Powered Lead Generation?" in expandable block
    with st.expander("Why Use AI-Powered Lead Generation?"):
        st.subheader("⚡ Speed & Efficiency")
        st.write("Generate leads 10x faster than manual methods")
        
        st.subheader("🎯 Precision Targeting")
        st.write("Identify prospects that match your ideal customer profile")
        
        st.subheader("📊 Data-Driven Insights")
        st.write("Make informed decisions based on comprehensive research")

# Results area (initially hidden)
results_container = st.container()

# Initialize session state for persistent storage
if 'results' not in st.session_state:
    st.session_state.results = None
if 'pricing_tracker' not in st.session_state:
    st.session_state.pricing_tracker = ModelsPricing()

# Update the run button section to preserve state
if run_button:
    if not industry or not country:
        st.error("Please enter an industry and country")
    elif not os.environ.get("OPENAI_API_KEY"):
        st.warning("⚠️ Please enter your OpenAI API key in the sidebar to continue")
    else:
        with st.status("🤖 Researching... This may take several minutes.", expanded=True) as status:
            try:
                # Clear module caches before initialization
                clear_module_cache()
                
                # Initialize the crew with caching
                @st.cache_resource(ttl=3600)  # Cache for 1 hour
                def get_lead_generator(serper_api_key=None):
                    logger.info("Creating new LeadGenerator instance")
                    return LeadGenerator(serper_api_key=serper_api_key)
                
                # Initialize the lead generator
                lead_gen = get_lead_generator(serper_api_key=config.get('serper_api_key'))
                
                # Create the crew instance
                crew = lead_gen.crew()  # Call the crew method to get the Crew instance
                
                # Run the crew with industry and country inputs
                results = crew.kickoff(inputs={
                    "industry": industry,
                    "country": country
                })
                
                # Store results in session state immediately
                st.session_state.results = results
                status.update(label="✅ Lead generation completed!", state="complete", expanded=False)
                
                # Now let's process the results first
                with results_container:
                    st.success("✅ Lead generation process completed successfully!")
                    
                    st.markdown("### Your Leads are ready!")
                    
                    try:
                        # Get the results from the CrewOutput object
                        results = st.session_state.results
                        results_list = []  # Initialize empty list
                        
                        # Try to get the last task's output
                        if hasattr(results, 'tasks_output') and results.tasks_output:
                            last_task = results.tasks_output[-1]
                            if hasattr(last_task, 'raw'):
                                raw_output = last_task.raw
                                try:
                                    # Try to extract JSON from markdown code block if present
                                    if '```json' in raw_output:
                                        # Extract content between ```json and ```
                                        json_str = raw_output.split('```json')[1].split('```')[0].strip()
                                        parsed = json.loads(json_str)
                                    else:
                                        # Try to parse as regular JSON
                                        parsed = json.loads(raw_output)
                                    
                                    # Ensure it's a list
                                    if isinstance(parsed, list):
                                        results_list = parsed
                                    elif isinstance(parsed, dict):
                                        results_list = [parsed]
                                    else:
                                        results_list = [{"raw_output": str(raw_output)}]
                                        
                                except (json.JSONDecodeError, IndexError, AttributeError) as e:
                                    # If parsing fails, store the raw output for debugging
                                    results_list = [{"raw_output": str(raw_output)}]
                            else:
                                # Fallback to raw attribute if it exists
                                try:
                                    raw_output = results.raw if hasattr(results, 'raw') else str(results)
                                    if '```json' in raw_output:
                                        json_str = raw_output.split('```json')[1].split('```')[0].strip()
                                        parsed = json.loads(json_str)
                                    else:
                                        parsed = json.loads(raw_output)
                                    results_list = [parsed] if isinstance(parsed, dict) else parsed if isinstance(parsed, list) else [{"raw_data": str(raw_output)}]
                                except (json.JSONDecodeError, IndexError, AttributeError):
                                    results_list = [{"error": "Could not parse results", "raw": str(raw_output)[:500] + ('...' if len(str(raw_output)) > 500 else '')}]
                        else:
                            # If no tasks_output, try raw directly
                            try:
                                raw_output = results.raw if hasattr(results, 'raw') else str(results)
                                if '```json' in raw_output:
                                    json_str = raw_output.split('```json')[1].split('```')[0].strip()
                                    parsed = json.loads(json_str)
                                else:
                                    parsed = json.loads(raw_output)
                                results_list = [parsed] if isinstance(parsed, dict) else parsed if isinstance(parsed, list) else [{"raw_data": str(raw_output)}]
                            except (json.JSONDecodeError, IndexError, AttributeError):
                                results_list = [{"error": "No valid results found", "raw": str(raw_output)[:500] + ('...' if len(str(raw_output)) > 500 else '')}]
                        
                        # Store the parsed results in session state for download
                        st.session_state.results_list = results_list
                        
                        # Display results
                        for idx, lead in enumerate(results_list, 1):
                            if not isinstance(lead, dict):
                                continue
                            
                            # Create an expander for each company
                            with st.expander(f"🏢 {idx}. {lead.get('company_name', 'Unknown Company')} (Score: {lead.get('score', 'N/A')}/10)", expanded=False):
                                # Company header with score-based color
                                score = float(lead.get('score', 0))
                                if score >= 8:
                                    header_color = "green"
                                elif score >= 6:
                                    header_color = "orange"
                                else:
                                    header_color = "gray"
                                
                                st.markdown(f"<h3 style='color: {header_color};'>{lead.get('company_name', 'N/A')}</h3>", unsafe_allow_html=True)
                                
                                col1, col2 = st.columns([3, 2])
                                
                                with col1:
                                    st.markdown("#### Company Information")
                                    st.markdown(f"**Annual Revenue:** {lead.get('annual_revenue', 'N/A')}")
                                    
                                    location = lead.get('location', {})
                                    if isinstance(location, dict):
                                        st.markdown(f"**Location:** {location.get('city', 'N/A')}, {location.get('country', 'N/A')}")
                                    else:
                                        st.markdown(f"**Location:** {location or 'N/A'}")
                                    
                                    website = lead.get('website_url', 'N/A')
                                    st.markdown(f"**Website:** [{website}]({website})" if website != 'N/A' else "**Website:** N/A")
                                    st.markdown(f"**Number of Employees:** {lead.get('num_employees', 'N/A')}")
                                
                                with col2:
                                    st.markdown("#### Company Profile")
                                    st.markdown(f"**Match Score:** {lead.get('score', 'N/A')}/10")
                                    st.progress(float(lead.get('score', 0)) / 10)
                                    
                                    # Display detailed information
                                    if 'review' in lead:
                                        st.markdown("#### Overview")
                                        st.write(lead['review'])
                                    
                                    if 'assessment' in lead:
                                        st.markdown("#### Assessment")
                                        st.write(lead['assessment'])
                                    
                                    # Show either sales_recommendations or recommendation field
                                    if 'sales_recommendations' in lead or 'recommendation' in lead:
                                        st.markdown("#### Sales Recommendations")
                                        st.write(lead.get('sales_recommendations', lead.get('recommendation', '')))
                                        
                                        # Store the recommendations in the lead for the report
                                        lead['_displayed_recommendations'] = lead.get('sales_recommendations', lead.get('recommendation', ''))
                                
                                st.markdown("#### Business Overview")
                                st.markdown(lead['review'] if 'review' in lead else 'N/A')
                                
                                if 'recommendations' in lead:
                                    st.markdown("#### Recommendations")
                                    st.markdown(lead['recommendations'])
                                
                                # Display key decision makers in markdown format
                                kdm = lead['key_decision_makers'] if 'key_decision_makers' in lead else []
                                if kdm:
                                    st.markdown("#### Key Decision Makers")
                                    for person in kdm:
                                        if isinstance(person, dict):
                                            name = person['name'] if 'name' in person else 'N/A'
                                            role = person['role'] if 'role' in person else 'N/A'
                                            linkedin = person['linkedin'] if 'linkedin' in person else '#'
                                            
                                            linkedin_link = f"[LinkedIn Profile]({linkedin})" if linkedin != '#' else 'N/A'
                                            st.markdown(f"**{name}** - {role} ({linkedin_link})")

                        # Add a JSON view option at the bottom
                        with st.expander("🔍 View Raw Data", expanded=False):
                            st.json(results_list)

                    except Exception as e:
                        st.error(f"Error displaying results: {str(e)}")
                        st.code(str(st.session_state.get('results', 'No results available')), language='json')
                        results_list = []  # Ensure it's defined even if there's an error
                    
                    # Download section - now uses results_list from session state
                    st.markdown("### 📥 Download Research Report")
                    download_data = "# Lead Generation Report\n\n"
                    
                    try:
                        results_list = st.session_state.get('results_list', [])
                        if not results_list:
                            download_data = "No results available to download."
                        else:
                            for lead in results_list:
                                if not isinstance(lead, dict):
                                    continue
                                    
                                company_name = lead.get('company_name', lead.get('company', 'Unnamed Company'))
                                download_data += f"## {company_name}\n\n"
                                
                                # Basic Info
                                download_data += "### Company Information\n"
                                download_data += f"- **Score:** {lead.get('score', 'N/A')}\n"
                                
                                # Handle location whether it's a string or dict
                                location = lead.get('location', {})
                                if isinstance(location, dict):
                                    loc_str = ", ".join(filter(None, [location.get('city'), location.get('country')]))
                                    if loc_str:
                                        download_data += f"- **Location:** {loc_str}\n"
                                elif location:
                                    download_data += f"- **Location:** {location}\n"
                                
                                # Add website and employee count if available
                                if 'website_url' in lead or 'link' in lead:
                                    download_data += f"- **Website:** {lead.get('website_url', lead.get('link', 'N/A'))}\n"
                                if 'num_employees' in lead:
                                    download_data += f"- **Employees:** {lead.get('num_employees', 'N/A')}\n"
                                
                                # Add review/overview
                                if 'review' in lead:
                                    download_data += "\n### Overview\n"
                                    download_data += f"{lead['review']}\n"
                                
                                # Add assessment if available
                                if 'assessment' in lead:
                                    download_data += "\n### Assessment\n"
                                    download_data += f"{lead['assessment']}\n"
                                
                                # Add sales recommendations if available
                                if 'sales_recommendations' in lead or 'recommendation' in lead or '_displayed_recommendations' in lead:
                                    recommendations = lead.get('_displayed_recommendations', 
                                                             lead.get('sales_recommendations', 
                                                                    lead.get('recommendation', '')))
                                    if recommendations:
                                        download_data += "\n### Sales Recommendations\n"
                                        download_data += f"{recommendations}\n"
                                
                                # Add key decision makers if available
                                kdm = lead.get('key_decision_makers', [])
                                if kdm and isinstance(kdm, list):
                                    download_data += "\n### Key Decision Makers\n"
                                    for person in kdm:
                                        if isinstance(person, dict):
                                            name = person.get('name', 'N/A')
                                            role = person.get('role', 'N/A')
                                            linkedin = person.get('linkedin', '')
                                            if linkedin:
                                                download_data += f"- **{name}** ({role}) - [LinkedIn]({linkedin})\n"
                                            else:
                                                download_data += f"- **{name}** ({role})\n"
                                
                                download_data += "\n---\n\n"
                            
                            # Also include raw JSON data at the end
                            download_data += "\n## Raw JSON Data\n\n```json\n"
                            download_data += json.dumps(results_list, indent=2, ensure_ascii=False)
                            download_data += "\n```\n"
                    
                    except Exception as e:
                        st.error(f"Error preparing download: {str(e)}")
                        download_data = f"Error generating report: {str(e)}"
                    
                    st.download_button(
                        label="📄 Download Full Report",
                        data=download_data,
                        file_name=f"lead_generation_report_{industry}_{country}.md",
                        mime="text/markdown"
                    )

                    # Usage metrics section
                    st.markdown("### 💰 Usage Metrics")
                    
                    try:
                        # Check for usage metrics in the crew object
                        if hasattr(crew, 'usage_metrics') and crew.usage_metrics:
                            metrics = crew.usage_metrics
                            
                            # Display the metrics in a clean format
                            with st.expander("🔍 View Usage Details", expanded=True):
                                if hasattr(metrics, 'total_tokens'):
                                    st.metric("Total Tokens Used", metrics.total_tokens)
                                if hasattr(metrics, 'prompt_tokens'):
                                    st.metric("Prompt Tokens", metrics.prompt_tokens)
                                if hasattr(metrics, 'completion_tokens'):
                                    st.metric("Completion Tokens", metrics.completion_tokens)
                                if hasattr(metrics, 'total_cost'):
                                    st.metric("Estimated Cost", f"${metrics.total_cost:.4f}")
                                    
                                # Show raw metrics - handle both Pydantic v1 and v2
                                try:
                                    # Try Pydantic v2 method first
                                    metrics_json = metrics.model_dump_json()
                                except AttributeError:
                                    # Fall back to Pydantic v1 method
                                    metrics_json = metrics.json()
                                st.json(json.loads(metrics_json))
                    except Exception as e:
                        st.warning(f"Could not display usage metrics: {str(e)}")
                
            except Exception as e:
                status.update(label="❌ Error occurred", state="error")
                st.error(f"An error occurred: {str(e)}")
                st.stop()
                
# Remove the duplicate results handling code
if __name__ == "__main__":
    # This is only used when running the script directly
    pass

# Add footer
footer_col1, footer_col2, footer_col3 = st.columns([1, 2, 1])
with footer_col2:
    st.caption("Made with ❤️ using AI-powered lead generation technology")
