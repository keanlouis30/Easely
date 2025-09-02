"""
Calendar Generator Module - The Administrative Assistant
======================================================

This module serves as Easely's expert spreadsheet generator, creating downloadable
.xlsx calendar files for premium users containing all their academic tasks and deadlines.

Core Responsibilities:
- Data fetching from the local database
- Data structuring for spreadsheet format
- Excel file generation using pandas and openpyxl
- Cloud storage upload for file delivery
- Temporary download link generation

Author: Easely Development Team
"""

import pandas as pd
import logging
import boto3
import io
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, BotoCoreError

from app.database.queries import get_all_upcoming_tasks
from config.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET_NAME, AWS_REGION

# Configure logging
logger = logging.getLogger(__name__)

class CalendarGeneratorError(Exception):
    """Custom exception for calendar generation related errors"""
    pass

class CalendarGenerator:
    """
    Administrative Assistant for generating downloadable calendar files
    """
    
    def __init__(self):
        """Initialize the calendar generator with cloud storage configuration"""
        # Validate AWS configuration
        if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET_NAME]):
            raise CalendarGeneratorError("AWS S3 configuration incomplete. Check environment variables.")
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION or 'us-east-1'
            )
            self.bucket_name = AWS_S3_BUCKET_NAME
            logger.info("S3 client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise CalendarGeneratorError("Failed to initialize cloud storage connection")
    
    def _fetch_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all upcoming tasks for a user from the database
        
        Args:
            user_id (str): The user's unique identifier
            
        Returns:
            List[Dict[str, Any]]: List of task dictionaries
            
        Raises:
            CalendarGeneratorError: If data fetching fails
        """
        try:
            logger.info(f"Fetching tasks for user: {user_id}")
            tasks = get_all_upcoming_tasks(user_id)
            
            if not tasks:
                logger.warning(f"No upcoming tasks found for user: {user_id}")
                return []
            
            logger.info(f"Successfully fetched {len(tasks)} tasks for user: {user_id}")
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to fetch tasks for user {user_id}: {e}")
            raise CalendarGeneratorError("Failed to retrieve your tasks from the database")
    
    def _structure_data_for_spreadsheet(self, tasks: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Structure task data into a pandas DataFrame suitable for Excel export
        
        Args:
            tasks (List[Dict[str, Any]]): Raw task data from database
            
        Returns:
            pd.DataFrame: Structured data ready for Excel generation
        """
        if not tasks:
            # Return empty DataFrame with proper structure
            return pd.DataFrame(columns=[
                'Task Title', 
                'Due Date', 
                'Due Time', 
                'Course Name', 
                'Task Type', 
                'Status'
            ])
        
        structured_data = []
        current_time = datetime.now(timezone.utc)
        
        for task in tasks:
            try:
                # Extract and format due date/time
                due_date = task.get('due_date')
                if due_date:
                    # Convert to local timezone if needed and format
                    if isinstance(due_date, str):
                        due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    
                    formatted_date = due_date.strftime('%Y-%m-%d')
                    formatted_time = due_date.strftime('%I:%M %p')
                    
                    # Determine task status
                    if due_date < current_time:
                        status = 'Overdue'
                    elif (due_date - current_time).days <= 1:
                        status = 'Due Soon'
                    else:
                        status = 'Upcoming'
                else:
                    formatted_date = 'No Date'
                    formatted_time = 'No Time'
                    status = 'Unknown'
                
                # Determine task type
                source = task.get('source', 'unknown')
                if source == 'canvas_sync':
                    task_type = 'Canvas Assignment'
                elif source == 'manual_entry':
                    task_type = 'Personal Task'
                else:
                    task_type = 'Unknown'
                
                # Structure the row
                row = {
                    'Task Title': task.get('title', 'Untitled Task'),
                    'Due Date': formatted_date,
                    'Due Time': formatted_time,
                    'Course Name': task.get('course_name', 'No Course'),
                    'Task Type': task_type,
                    'Status': status
                }
                
                structured_data.append(row)
                
            except Exception as e:
                logger.warning(f"Failed to process task: {task.get('title', 'Unknown')}, Error: {e}")
                # Add a minimal row for failed tasks
                structured_data.append({
                    'Task Title': task.get('title', 'Processing Error'),
                    'Due Date': 'Error',
                    'Due Time': 'Error',
                    'Course Name': task.get('course_name', 'Unknown'),
                    'Task Type': 'Error',
                    'Status': 'Error'
                })
        
        # Create DataFrame and sort by due date
        df = pd.DataFrame(structured_data)
        
        # Sort by due date (handle 'No Date' and 'Error' cases)
        def sort_key(date_str):
            if date_str in ['No Date', 'Error']:
                return datetime.max
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except:
                return datetime.max
        
        df['_sort_date'] = df['Due Date'].apply(sort_key)
        df = df.sort_values('_sort_date').drop('_sort_date', axis=1)
        
        logger.info(f"Successfully structured {len(df)} tasks for spreadsheet")
        return df
    
    def _generate_excel_file(self, df: pd.DataFrame, user_id: str) -> io.BytesIO:
        """
        Generate an Excel file in memory from the structured data
        
        Args:
            df (pd.DataFrame): Structured task data
            user_id (str): User identifier for personalization
            
        Returns:
            io.BytesIO: Excel file in memory buffer
        """
        try:
            # Create in-memory buffer
            buffer = io.BytesIO()
            
            # Generate timestamp for the file
            timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p')
            
            # Create Excel writer with openpyxl engine for better formatting
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                # Write main data to 'My Schedule' sheet
                df.to_excel(writer, sheet_name='My Schedule', index=False)
                
                # Get the workbook and worksheet for formatting
                workbook = writer.book
                worksheet = writer.sheets['My Schedule']
                
                # Add title and metadata
                worksheet.insert_rows(1, 3)
                worksheet['A1'] = f'Easely Academic Calendar'
                worksheet['A2'] = f'Generated: {timestamp}'
                worksheet['A3'] = f'Total Tasks: {len(df)}'
                
                # Format header row (now row 4)
                header_row = 4
                for col_num, column_title in enumerate(df.columns, 1):
                    cell = worksheet.cell(row=header_row, column=col_num)
                    cell.value = column_title
                    cell.font = workbook.create_font(bold=True)
                    cell.fill = workbook.create_fill(
                        fill_type='solid',
                        start_color='E6E6FA'  # Light lavender
                    )
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50 chars
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Add summary sheet if there are tasks
                if len(df) > 0:
                    summary_data = {
                        'Metric': [
                            'Total Tasks',
                            'Overdue Tasks', 
                            'Due Today/Tomorrow',
                            'Canvas Assignments',
                            'Personal Tasks'
                        ],
                        'Count': [
                            len(df),
                            len(df[df['Status'] == 'Overdue']),
                            len(df[df['Status'] == 'Due Soon']),
                            len(df[df['Task Type'] == 'Canvas Assignment']),
                            len(df[df['Task Type'] == 'Personal Task'])
                        ]
                    }
                    
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Format summary sheet
                    summary_sheet = writer.sheets['Summary']
                    summary_sheet['A1'].font = workbook.create_font(bold=True)
                    summary_sheet['B1'].font = workbook.create_font(bold=True)
            
            # Reset buffer position to beginning
            buffer.seek(0)
            logger.info(f"Successfully generated Excel file for user: {user_id}")
            return buffer
            
        except Exception as e:
            logger.error(f"Failed to generate Excel file for user {user_id}: {e}")
            raise CalendarGeneratorError("Failed to create calendar file")
    
    def _upload_to_s3(self, file_buffer: io.BytesIO, user_id: str) -> str:
        """
        Upload the Excel file to S3 and return a temporary download URL
        
        Args:
            file_buffer (io.BytesIO): Excel file in memory
            user_id (str): User identifier for file naming
            
        Returns:
            str: Temporary download URL (valid for 1 hour)
            
        Raises:
            CalendarGeneratorError: If upload fails
        """
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            filename = f"easely_calendar_{user_id}_{timestamp}_{unique_id}.xlsx"
            
            # Upload to S3
            logger.info(f"Uploading calendar file to S3: {filename}")
            self.s3_client.upload_fileobj(
                file_buffer,
                self.bucket_name,
                filename,
                ExtraArgs={
                    'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'ContentDisposition': f'attachment; filename="My_Easely_Calendar.xlsx"'
                }
            )
            
            # Generate presigned URL (valid for 1 hour)
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': filename},
                ExpiresIn=3600  # 1 hour
            )
            
            logger.info(f"Successfully uploaded and generated download URL for: {filename}")
            return download_url
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"S3 upload failed with error code {error_code}: {e}")
            raise CalendarGeneratorError("Failed to upload calendar file to cloud storage")
        
        except BotoCoreError as e:
            logger.error(f"AWS connection error: {e}")
            raise CalendarGeneratorError("Cloud storage connection failed")
        
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            raise CalendarGeneratorError("Failed to prepare calendar file for download")
    
    def create_and_upload_calendar_file(self, user_id: str) -> str:
        """
        Main public function to generate and upload a calendar file
        
        This orchestrates the entire process: data fetching, structuring,
        file generation, cloud upload, and URL generation.
        
        Args:
            user_id (str): The user's unique identifier
            
        Returns:
            str: Temporary download URL for the generated calendar file
            
        Raises:
            CalendarGeneratorError: If any step in the process fails
        """
        if not user_id or not user_id.strip():
            raise CalendarGeneratorError("User ID is required for calendar generation")
        
        try:
            logger.info(f"Starting calendar generation for user: {user_id}")
            
            # Step 1: Fetch user's task data
            tasks = self._fetch_user_tasks(user_id.strip())
            
            # Step 2: Structure data for spreadsheet
            df = self._structure_data_for_spreadsheet(tasks)
            
            # Step 3: Generate Excel file in memory
            file_buffer = self._generate_excel_file(df, user_id)
            
            # Step 4: Upload to S3 and get download URL
            download_url = self._upload_to_s3(file_buffer, user_id)
            
            logger.info(f"Successfully completed calendar generation for user: {user_id}")
            return download_url
            
        except CalendarGeneratorError:
            # Re-raise CalendarGeneratorError as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error in calendar generation for user {user_id}: {e}")
            raise CalendarGeneratorError("An unexpected error occurred during calendar generation")


# Convenience function for easy importing
def create_and_upload_calendar_file(user_id: str) -> str:
    """
    Convenience function to generate and upload a calendar file
    
    This is the primary interface that other modules should use.
    
    Args:
        user_id (str): The user's unique identifier
        
    Returns:
        str: Temporary download URL for the generated calendar file
        
    Raises:
        CalendarGeneratorError: If calendar generation fails
    """
    generator = CalendarGenerator()
    return generator.create_and_upload_calendar_file(user_id)


# Example usage and testing functions
if __name__ == "__main__":
    """
    Basic testing functionality - only runs when script is executed directly
    """
    # Example test case
    test_user_id = "test_user_123"
    
    try:
        print(f"Generating calendar for user: {test_user_id}")
        download_url = create_and_upload_calendar_file(test_user_id)
        print("Calendar generated successfully!")
        print(f"Download URL: {download_url}")
    except CalendarGeneratorError as e:
        print(f"Error generating calendar: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")