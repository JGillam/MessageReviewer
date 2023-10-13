import json
import os
import argparse
from extract_msg import Message
from dateutil.parser import parse
import datetime
import re

# Encoding function to encode the email addresses to be used in the HTML
def encode_email(email):
    if email is None:
        return None
    else:
        return email.replace("<", "&lt;").replace(">", "&gt;")

def encode_filename(filename):
    if filename is None:
        return None
    else:
        return filename.replace(" ", "_").replace("#", "_")

# Attempt to parse the encoding out of the html_body, which will be a bytes object.
def get_charset_from_msg(html_body):
    # Try to parse the encoding from the html_body
    charset = None
    try:
        charset = re.search(rb'charset=([\w-]+)', html_body).group(1)
    except AttributeError:
        pass
    # return the charset as a string if it was found, otherwise return None
    if charset is not None:
        return charset.decode('utf-8')
    else:
        return None

if __name__ == '__main__':
    # Initialize Argument Parser
    parser = argparse.ArgumentParser(description="Generate a JSON file and HTML interface for reviewing .msg files.")
    parser.add_argument("path",
                        help="The directory path where .msg files are stored and where output files will be placed.")
    args = parser.parse_args()

    # Set the directory path based on the argument args.path. It must be friendly for Windows and Linux.
    directory = os.path.abspath(args.path.strip("'\""))

    # Set the output paths based on the argument. These should work for both Windows and Linux.
    revmsg_folder = os.path.join(directory, 'revmsg')
    if not os.path.exists(revmsg_folder):
        os.makedirs(revmsg_folder)

    attachments_folder = os.path.join(revmsg_folder, 'attachments')

    html_output_path = os.path.join(revmsg_folder, 'index.html')

    # To provide some output, lets get a count of the number of files in the directory that end with .msg (case insensitive)
    file_count = len([file for file in os.listdir(directory) if file.lower().endswith('.msg')])
    print(f"Found {file_count} .msg files in {directory}")
    counter = 0
    attachment_index = 1

    # Extract email data
    emails = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.msg'):
            counter += 1
            print(f"Processing [{counter}/{file_count}]: {filename}")
            filepath = os.path.join(directory, filename)
            msg: Message = Message(filepath)

            # Produce a formatted date string based on the send date of the message
            date = msg.date
            formatted_date = 'Unknown'

            if isinstance(msg.date, datetime.datetime):
                date = msg.date
                formatted_date = f"{date.month}/{date.day}/{date.year} {date.hour}:{date.minute}:{date.second}"
            elif isinstance(msg.date, str):
                try:
                    date = parse(msg.date)
                    formatted_date = f"{date.month}/{date.day}/{date.year} {date.hour}:{date.minute}:{date.second}"
                except ValueError:
                    # If parsing fails, keep it as a string
                    formatted_date = msg.date

            # Save the .html version of the file into the revmsg folder using extract_msg.  Slice the filename to remove the .msg extension
            SaveType, path = msg.save(customPath=revmsg_folder, customFilename=encode_filename(filename[:-4]), preparedHtml=True, html=True, overwrite=True)
            folder_name = os.path.basename(path)
            print(f"Saved {filename} as {folder_name}")

            # Iterate through the files saved by msg.save() and make a list of all the filenames
            attachments = []
            for file in os.listdir(path):
                attachments.append(file)

            # Some of the msg files are from Outlook and have a body attribute.  Others are from Exchange and have a htmlBody.
            # Set the body appropriately based on which attribute exists.
            if hasattr(msg, 'htmlBody') and msg.htmlBody is not None:
                message_body = msg.htmlBody
            elif hasattr(msg, 'body') and msg.body is not None:
                message_body = msg.body
            else:
                message_body = "[No message body]"

            # Test if message body is a bytes object, if so, convert it to a string
            if isinstance(message_body, bytes):
                try:
                    message_body = message_body.decode('utf-8')
                except UnicodeDecodeError:
                    encoding = get_charset_from_msg(message_body)
                    if encoding is not None:
                        message_body = message_body.decode(encoding)
                    else:
                        message_body = "[Unable to decode message body, try opening message.html above]"


            email_data = {
                'id': filename,
                'subject': msg.subject,
                'date': formatted_date,
                'from': encode_email(msg.sender),
                'to': encode_email(msg.to),
                'cc': encode_email(msg.cc),
                'body': message_body,
                'folder_name': folder_name,
                'attachments': attachments
            }

            emails.append(email_data)

    script_directory = os.path.dirname(os.path.abspath(__file__))
    html_source_path = os.path.join(script_directory, 'index.html')

    # Read the HTML template and replace the <!--JSON_PLACEHOLDER--> with the JSON data, where it will be assigned to the emails variable
    with open(html_source_path, 'r') as f:
        html_template = f.read()
        html_template = html_template.replace('<!--JSON_PLACEHOLDER-->', "emails=" + json.dumps(emails) + ";")

    # Write the HTML template to the revmsg directory
    with open(html_output_path, 'w') as f:
        f.write(html_template)





