from zjooc import ZJOOC
from rich.console import Console
from rich.table import Table

def display_courses(course_data):
    """Displays the course data in a rich table."""
    console = Console()

    # Create a Table object with headers and styles
    table = Table(show_header=True, header_style="bold green", title="Course List", title_style="yellow")
    table.add_column("Course Name", justify="center")
    table.add_column("Course ID", justify="center")

    # Add rows to the table from the course data
    for course in course_data:
        table.add_row(course['courseName'], course['courseId'])

    # Print the table
    console.print(table)

def get_user_input():
    """Prompt for user input and return username and password."""
    usernam = input("Enter your username: ")
    pwd = input("Enter your password: ")
    return usernam, pwd

def main():
    # Get user input for credentials
    username, password = get_user_input()

    # Initialize ZJOOC with user credentials
    user = ZJOOC(username=username, pwd=password)

    # Get course data by sending "msg 4" request
    course_data = user.paser("msg 4")

    if not course_data:
        print("No course data found.")
        return

    # Display the course data in a table
    display_courses(course_data)

    # Input loop for course selection
    while True:
        course_id = input("请输入你想要刷课的Course ID（输入 'exit' 退出程序）: ")
        
        if course_id.lower() == 'exit':
            print("Exiting the program.")
            break

        # Attempt to perform the action for the selected course ID
        try:
            user.paser(f'do 1 {course_id}')
            print(f"Successfully started the course: {course_id}.")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
