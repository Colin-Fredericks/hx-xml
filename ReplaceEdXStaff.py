# VPAL Multi-course Staffing Script

instructions = """
to run:
python3 ReplaceEdXStaff.py -f filename.csv

The csv file must have these headers/columns:
URL - the address of class' Course Team Settings page
Add - the e-mail addresses of the staff to be added. (not usernames)
      If there are multiple staff, space-separate them.
Remove - just like "Add".

The output is another CSV file that shows which courses couldn't be accessed
and which people couldn't be removed.
"""

# Current locations of items in edX:
# Logging in
login_page = "https://authn.edx.org/login"
# Adding staff
new_team_button = "a.create-user-button"
new_staff_email_input = "input#user-email-input"
add_user_button = "div.actions button.action-primary"
# Removing staff
staff_email_location = "span.user-email"
remove_user_button = "a.remove-user" # This will have data-id = the email address.

num_classes = 0
num_classes_fixed = 0
skipped_classes = []
unfound_addresses = []

# Read in command line arguments.
# Prompt for username and password
# Open the csv and read it to a dict
# Duplicate that dict for output purposes. It'll show who we couldn't remove.
# Add a key to the new dict to show whether we could access the course.
# Open the edX sign-in page, currently https://authn.edx.org/login
# Sign in
# For each line in the CSV...
    # Open the URL.
    # If we can't open the URL:
        # Make a note and skip this course.
    # Wait for load.
    # If we have people to add...
        # Split the Add string by spaces
        # For each Add address:
            # Click the "New Team Member" button
            # Put the e-mail into the input box
            # Click "Add User"
            # Wait for load.
            # If there's an error message:
                # Make a note and move on.
            # Otherwise
                # Remove that e-mail address from the Add list in the new dict.
    # If we have people to remove...
        # Split the Remove string by spaces
        # For each Remove address:
            # Find the e-mail address on the page.
            # Click the trash can ("remove user" button)
            # Wait for load.
            # If there's an error message:
                # Make a note and move on.
            # Otherwise
                # Remove that e-mail address from the Remove list in the new dict.

# Write out a new csv.
# Done.
