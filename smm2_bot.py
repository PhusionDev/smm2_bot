#!/usr/bin/env python

import socket
import logging
import re
from os import path
from emoji import demojize

basepath = path.dirname(__file__)
config_file = path.abspath(path.join(basepath, "config.txt"))
commands_file = path.abspath(path.join(basepath, "commands.txt"))
ignored_file = path.abspath(path.join(basepath, "ignore_list.txt"))
queue_file = path.abspath(path.join(basepath, "queue.txt"))

def main():
    config_file_lines = []
    config_line_index = {}
    ignored_file_lines = []
    ignored_file_add_newline = False
    ignored_user_index = {}
    commands_list = []
    commands_string = ''
    commands_re = ''
    queue_file_add_newline = False
    queue_file_lines = []
    queue_line_index = {}   # key, value = {user_info_string, line_num}
    queue_course_id = {}  # key, value = {user_info_string, course_id}
    queue_position = {} # key, value = {user_info_string, position}
    queue_list = [] # stores a user_info_string
    commands = {}   # key, value = {command_name, command}
    config = {} # key, value = {config_term, config_value}
    
    # queue taking submissions?
    queue_is_open = True
    
    def get_list_from_cfg_line(line):
        contents_found = re.search("\[.*\]",line)
        if (contents_found):
            contents = contents_found.group(0)
            contents = re.sub("\[|\]","",contents)
            if not (contents == ''):
                return contents.split(',')
            return []
        return
        
    def get_value_from_cfg_line(line):
        value = ''
        if not (re.search('(^#|^$)',line)):
            value_found = re.search("\".*\"",line)
            if (value_found):
                value = value_found.group(0)
                value = re.sub("\"","",value)
            else:
                list_value = get_list_from_cfg_line(line)
                if not (list_value):
                    value = list_value
        return value
        
    def convert_value_to_user_info(value):
        if (re.search(':',value)):
            value = re.sub('\n','',value)
            split_value = value.split(':')
            return (split_value[0].lower(),split_value[1].lower())
    
    def get_cfg_line_ignored_users():
        index = 0
        for line in config_file_lines:
            if line.startswith('ignore_list: '):
                return index
            else:
                index += 1
        return -1
    
    def is_debug_mode():
        if config['debug_mode'].lower() in ['true','yes','y','on']:
            return True
        else:
            return False
    
    def is_streamer(username):
        if (username == config['streamer_name']):
            return True
            
    def is_admin(username):
        if (is_streamer(username)):
            return True
        else:
            for admin in config['admins']:
                if (username.lower() == admin.lower()):
                    return True
        return False
    
    def is_mod(username):
        if (is_streamer(username)):
            return True
        else:
            for mod in config['mods']:
                if (username.lower() == mod.lower()):
                    return True
        return False
        
    def is_relay_bot(username):
        if (username.lower() == config['relay_bot_name'].lower()):
            return True
        else:
            if (is_debug_mode() and username.lower() == config['streamer_name'].lower()):
                return True
            return False
            
    def course_is_unique(course_id):
        unique = True
        course_id = format_course_id(course_id)
        if (len(queue_list) > 0):
            for user, course in queue_course_id.items():
                if (course == course_id):
                    unique = False
                    break
        return unique
    
    def user_is_unique(user_info_string):
        if user_info_string in queue_list:
            return False
        else:
            return True
        
    def chat(msg):
        sock.send("PRIVMSG #{} :{}\r\n".format(config['streamer_name'], msg).encode('utf-8'))
    
    def debug_queue():
        print("Queue List: " + str(queue_list))
        print("Queue Course ID Dictionary: " + str(queue_course_id))
        print("Queue File Line Index Dictionary: " + str(queue_line_index))
        print("Queue Position Dictionary: " + str(queue_position))
        
    def clear_queue():
        # check for entries in queue
        if (len(queue_list) > 0):
            # get lines to remove from queue_file_lines
            clear_lines = []
            for user_info_string in queue_list:
                clear_lines.append(queue_line_index[user_info_string])
            # sort list descending
            clear_lines.sort(reverse=True)
            # remove those lines from the list
            for index in clear_lines:
                queue_file_lines.pop(index)
            # save the lines to file
            with open(queue_file,'w',encoding="utf8") as file:
                file.writelines(queue_file_lines)
            # clear the queue_list list and the dictionaries: queue_position, queue_course_id, queue_line_index
            queue_list.clear()
            queue_position.clear()
            queue_course_id.clear()
            queue_line_index.clear()
            return ('The queue has been cleared/reset!')
        return ('There are already no entries in the queue!')
                
    def add_course_from_message(username, message):
        user_info = get_user_info(username, message)
        user_info_string = convert_user_info_to_string(user_info)
        course_id = get_course_id(message)
        msg = add_course(user_info_string, course_id)
        return msg
    
    def add_course(user_info_string, course_id,force_add=False):
        nonlocal queue_file_add_newline
        user_info = convert_value_to_user_info(user_info_string)
        msg = user_info[0] + " from " + user_info[1] + ": "
        if (queue_is_open or force_add):
            if not (course_id == 'Invalid Course ID'):
                if (course_is_unique(course_id)):
                    if (user_is_unique(user_info_string)):
                        new_line = user_info_string + ' "' + course_id + '"\n'
                        queue_course_id[user_info_string] = course_id
                        queue_file_lines.append(new_line)
                        queue_list.append(user_info_string)
                        queue_position[user_info_string] = len(queue_list)
                        queue_line_index[user_info_string] = len(queue_file_lines) - 1
                        with open(queue_file,'a',encoding="utf8") as file:
                            if (queue_file_add_newline):
                                file.write('\n')
                                queue_file_add_newline = False
                            file.write(new_line)
                        msg = msg + "your course: " + course_id
                        if (queue_position[user_info_string] == 1):
                            msg = msg + " is up next!"
                        else:
                            msg = msg + " has been added to the queue in position: " + str(queue_position[user_info_string])
                    else:
                        msg = msg + "you are already entered in the queue, please wait until your course has been played first!"
                else:
                    msg = msg + "that course id is already in the queue!"
            else:
                msg = msg + "that course is an invalid course id!"
        else:
            msg = msg + "Sorry, but the queue is currently not taking any more submissions."
        return msg
        
    def remove_course(position):
        reindex = True
        if (position > 0):
            if (len(queue_course_id) >= position):
                if (position == len(queue_list)):
                    reindex = False
                index = position - 1
                user_info_string = queue_list[index]
                user_info = convert_value_to_user_info(user_info_string)
                queue_list.pop(index)
                queue_file_lines.pop(queue_line_index[user_info_string])
                with open(queue_file,'w',encoding="utf8") as file:
                    file.writelines(queue_file_lines)
                del queue_position[user_info_string]
                del queue_line_index[user_info_string]
                del queue_course_id[user_info_string]
                msg = user_info[0] + " from " + user_info[1] + ": your course in position " + str(position) + " has been removed from the queue."
            else:
                msg = 'That position is greater than the amount of courses in the queue.'
        else:
            msg = 'There are no courses in the queue to remove.'
        if (reindex):
            reindex_queue_from_position(position)
        return msg
    
    def reindex_queue_from_position(position):
        for pos in range(position,len(queue_list) + 1,1):
            user_info_string = queue_list[pos -1]
            queue_line_index[user_info_string] -= 1
            queue_position[user_info_string] -= 1
            
    def exchange_course(username, message):
        user_info = get_user_info(username, message)
        user_info_string = convert_user_info_to_string(user_info)
        msg = ''
        if user_info_string in queue_position:
            course_id = get_course_id(message)
            if not (course_id == 'Invalid Course ID'):
                queue_course_id[user_info_string] = course_id
                queue_file_lines[queue_line_index[user_info_string]] = user_info_string + ' "' + course_id + '"\n'
                with open(queue_file,'w',encoding="utf8") as file:
                    file.writelines(queue_file_lines)
                msg = user_info[0] + " from " + user_info[1] + ": your entry in position " + str(queue_position[user_info_string]) + " has been changed to " + course_id
            else:
                msg = user_info[0] + " from " + user_info[1] + ": your new entry is an invalid ID."
        else:
            msg = user_info[0] + " from " + user_info[1] + ": you are not currently in the queue!"
        return msg
    
    def leave_queue(username, message):
        user_info = get_user_info(username, message)
        user_info_string = convert_user_info_to_string(user_info)
        if user_info_string in queue_course_id:
            position = queue_position[user_info_string]
            if (position == 1):
                msg = user_info[0] + " from " + user_info[1] + ": Your course is currently up/being played. " + config['streamer_name'] + " will decide to finish the course or not. Thanks for your submission!"
            else:
                msg = remove_course(position)
                msg = msg + " Come back soon!"
        else:
            msg = user_info[0] + " from " + user_info[1] + ": you are not currently in the queue!"
        return msg
        
    def get_course_id(message):
        re_cmds = "(" + commands['add_course'] + "|" + commands['exchange_course'] + ") "
        re_str =  re_cmds + "[a-hj-np-yA-HJ-NP-Y0-9]{3}[- ][a-hj-np-yA-HJ-NP-Y0-9]{3}[- ][a-hj-np-yA-HJ-NP-Y0-9]{3}"
        course_id = ''
        course_re = re.search(re_str, message)
        if (course_re):
            course_string = course_re.group(0)
            course_id = re.sub(re_cmds,'',course_string)
        else:
            return 'Invalid Course ID'
        return format_course_id(course_id)
    
    def get_user_info(username, message):
        if (is_relay_bot(username)):
            restream_string = get_restream_string(message)
            if (restream_string == '' and is_debug_mode):
                return ((config['streamer_name'],'twitch'))
            else:
                return (get_restream_username(restream_string), get_restream_source(restream_string))
        else:
            return (username, 'twitch')
    
    def convert_user_info_to_string(user_info):
        if (len(user_info) == 2):
            platform = user_info[1].lower()
            platform_found = re.search('(mixer|twitch|youtube|facebook|twitter|discord|dlive|mobcrush)',platform)
            if (platform_found):
                return user_info[0].lower() + ':' + platform
        
    def get_course_info(username, message):
        source = 'twitch'
        course_id = get_course_id(message)
        user_info = get_user_info(username, message)
        return (user_info[0], user_info[1], course_id)
        
    def get_restream_string(message):
        restream_string = ''
        rs_re = re.search('\[(Mixer:|YouTube:|Facebook:|Twitter:|Discord:|DLive:|Mobcrush:) .*\]', message)
        if(rs_re):
            restream_string = rs_re.group(0)
            
        return restream_string
        
    def get_restream_source(restream_string):
        restream_source = ''
        rs_re = re.search('(Mixer|YouTube|Facebook|Twitter|Discord|DLive|Mobcrush)', restream_string)
        if(rs_re):
            restream_source = rs_re.group(0)
        
        return restream_source
    
    def get_restream_username(restream_string):
        restream_username = re.sub('\[|\]|(Mixer: )|(YouTube: )|(Facebook: )|(Twitter: )|(Discord: )|(DLive: )|(Mobcrush: )','',restream_string)
        return restream_username
    
    def format_course_id(course_id):
        course_id = course_id.upper()
        course_id = re.sub(' ','-',course_id)
        return course_id
        
    def next_course():
        msg = ''
        if (len(queue_list) > 0):
            user_info = convert_value_to_user_info(queue_list[0])
            course_id = queue_course_id[queue_list[0]]
            msg = "The next course is: " + course_id + " by " + user_info[0] + " from " + user_info[1]
        else:
            msg = empty_queue_message()

        return msg
    
    def get_full_queue():
        msg = "Current Queue:"
        if (len(queue_list) > 0):
            position = 0
            for user_info_string in queue_list:
                position += 1
                if (position > 1):
                    msg = msg + ","
                msg = msg + ' ' + str(position) + '. ' + user_info_string
        else:
            msg = empty_queue_message()
            
        return msg
    
    def empty_queue_message():
        if (queue_is_open):
            return "The queue is currently empty. Type " + commands['add_course'] + " xxx-xxx-xxx or " + commands['add_course'] + " xxx xxx xxx to submit a course!"
        else:
            return "The course queue is currently empty, but no longer taking submissions. Thanks for all of your courses everybody! Please come back next stream to submit more!"
            
    def skip_current_course():
        course_count = len(queue_list)
        if (course_count > 1):
            cur_user_info_string = queue_list[0]
            cur_user_info = convert_value_to_user_info(cur_user_info_string)
            cur_course_id = queue_course_id[cur_user_info_string]
            cur_queue_line_index = queue_line_index[cur_user_info_string]
            cur_line = queue_file_lines[cur_queue_line_index]
            next_user_info_string = queue_list[1]
            next_user_info = convert_value_to_user_info(next_user_info_string)
            next_course_id = queue_course_id[next_user_info_string]
            next_queue_line_index = queue_line_index[next_user_info_string]
            next_line = queue_file_lines[next_queue_line_index]
            # Change the queue_file_lines
            queue_file_lines[next_queue_line_index] = cur_line
            queue_file_lines[cur_queue_line_index] = next_line
            # Update the queue file line index dictionary
            queue_line_index[next_user_info_string] = cur_queue_line_index
            queue_line_index[cur_user_info_string] = next_queue_line_index
            # Save the queue file
            with open(queue_file,'w',encoding="utf8") as file:
                file.writelines(queue_file_lines)
            # Update the position dictionary
            queue_position[cur_user_info_string] += 1
            queue_position[next_user_info_string] -= 1
            # Update the queue list
            queue_list[0] = next_user_info_string
            queue_list[1] = cur_user_info_string
                    
            msg = "The current course has been skipped, up next is " + next_course_id + " by " + next_user_info[0] + " from " + next_user_info[1]
        elif (course_count == 1):
            msg = "There is only one course in the queue; unable to skip to another course!"
        else:
            msg = "There are currently no courses in the queue to skip to or from!"
        return msg
    
    def move_course_to_end():
        if (len(queue_list) > 1):
            user_info_string = queue_list[0]
            user_info = convert_value_to_user_info(user_info_string)
            course_id = queue_course_id[user_info_string]
            remove_course(1)
            add_course(user_info_string, course_id,True)
            return user_info[0] + " from " + user_info[1] + ": your course has been moved to the end of the queue. " + next_course()
        else:
            return "There is only one course in the queue. Cannot move to the end because it's already there!"
        
    def command_in_message(message):
        result = re.search(commands_re,message)
        if (result):
            command = result.group(0)
            command = re.sub('($|\s)','',command)
            return (True,command)
        return (False,'')
    
    def show_user_commands():
        msg = commands['add_course'] + " "  + commands['leave_queue'] + " " + commands['exchange_course'] + " " + commands['show_current_course'] + " " + commands['show_queue_count'] + " " + commands['show_position_in_queue'] + " " + commands['show_queue_list'] + " " + commands['show_commands']
        return msg
    
    def is_ignored_user(username, message):
        user_info = get_user_info(username, message)
        return ignoring_user(user_info)
    
    def ignoring_user(user_info):
        user_string = convert_user_info_to_string(user_info)
        if (user_string):
            if user_string in ignored_user_index:
                return True
        return False
        
    def ignore_user(message):
        nonlocal ignored_file_add_newline
        msg = ''
        message = message.lower()
        ignore_re = commands['ignore_user'] + " .*:(mixer|twitch|youtube|facebook|twitter|dlive|mobcrush)"
        match = re.search(ignore_re,message)
        if (match):
            ignore_user_str = re.sub(commands['ignore_user'] + " ",'',match.group(0))
            user_info = convert_value_to_user_info(ignore_user_str)
            if (user_info):
                if not (ignoring_user(user_info)):
                    user_info_string = convert_user_info_to_string(user_info)
                    new_ignore_str = ignore_user_str + '\n'
                    ignored_file_lines.append(new_ignore_str)
                    ignored_user_index[user_info_string] = len(ignored_file_lines) - 1
                    msg = "I'm now ignoring " + user_info[0] + " from " + user_info[1]
                    with open(ignored_file, 'a', encoding="utf8") as file:
                        if (ignored_file_add_newline):
                            file.write('\n')
                            ignored_file_add_newline = False
                        file.write(new_ignore_str)
                else:
                    msg = "I'm already ignoring " + user_info[0] + " from " + user_info[1]
            else:
                msg = "I couldn't convert the user and platform!"
        else:
            msg = "I couldn't find a valid user and platform to ignore!"
        return msg
    
    def unignore_user(message):
        msg = ''
        message = message.lower()
        unignore_re = commands['unignore_user'] + " .*:(mixer|twitch|youtube|facebook|twitter|dlive|mobcrush)"
        match = re.search(unignore_re,message)
        if (match):
            ignore_user_str = re.sub(commands['unignore_user'] + " ",'',match.group(0))
            user_info = convert_value_to_user_info(ignore_user_str)
            if (user_info):
                if (ignoring_user(user_info)):
                    msg = "I'm no longer ignoring " + user_info[0] + " from " + user_info[1]
                    user_info_string = convert_user_info_to_string(user_info)
                    line_index = ignored_user_index[user_info_string]
                    del ignored_user_index[user_info_string]
                    ignored_file_lines.pop(line_index)
                    reindex_ignored_users_above_index(line_index)
                    with open(ignored_file, 'w', encoding="utf8") as file:
                        file.writelines(ignored_file_lines)
                else:
                    msg = "I'm not currently ignoring " + user_info[0].lower() + " from " + user_info[1].lower()
            else:
                msg = "I couldn't convert the user's info and platform"
        else:
            msg = "I couldn't find a valid user and platform to stop ignoring"
        return msg
                    
    def reindex_ignored_users_above_index(value):
        for ignored_user, index in ignored_user_index.items():
            if (index > value):
                ignored_user_index[ignored_user] = index - 1
                
    def toggle_debug_mode():
        msg = ''
        if (is_debug_mode()):
            msg = 'Debug mode is now off'
            config['debug_mode'] = 'false'
        else:
            msg = 'Debug mode is now on'
            config['debug_mode'] = 'true'
        config_file_lines[config_line_index['debug_mode']] = 'debug_mode: "' + config['debug_mode'] + '"\n'
        with open(config_file, 'w', encoding="utf8") as file:
            file.writelines(config_file_lines)
        return msg
    
    def request_song(username, message):
        msg = ''
        user_info = get_user_info(username, message)
        if not (user_info[1] == 'twitch'):
            re_str = commands['song_request'] + " .*"
            sr_re = re.search(re_str, message)
            if (sr_re):
                sr_str = sr_re.group(0)
                msg = sr_str
        return msg

        
    with open(config_file, encoding="utf8") as file:
        config_file_lines = file.readlines()
        line_num = 0
        for line in config_file_lines:
            value = get_value_from_cfg_line(line)
            if not (value == ''):
                config_found = re.search('^.*: {1}',line)
                if (config_found):
                    config_name = config_found.group(0)
                    config_name = re.sub(': {1}','',config_name)
                    if not (config_name == ""):
                        config[config_name] = value
                        config_line_index[config_name] = line_num
            
            line_num += 1
            
    print("SMM2 bot by LoveDollRomance is active for: " + config['streamer_name'])
    print("I am working under the alias of: " + config['bot_name'])
    print("The multi-platform chat relay bot I will respond to is: " + config['relay_bot_name'])
    print("Admins: " + str(config['admins']))
    print("Mods: " + str(config['mods']))

    with open(ignored_file, encoding="utf8") as file:
        ignore_str = 'Ignoring: '
        ignored_file_lines = file.readlines()
        line_num = 0
        for line in ignored_file_lines:
            if not (re.search('(^#|^$)',line)):
                line = line.lower()
                ignore_line_found = re.search(".*:(mixer|twitch|youtube|facebook|twitter|dlive|mobcrush)",line)
                if (ignore_line_found):
                    ignored_user_string = ignore_line_found.group(0)
                    ignored_user_index[ignored_user_string] = line_num
                    ignored_user_info = convert_value_to_user_info(line)
                    if (ignored_user_info):
                        ignore_str = ignore_str + ignored_user_info[0] + " from " + ignored_user_info[1] + ", "
            line_num += 1
        last_line_index = len(ignored_file_lines) - 1
        last_line = ignored_file_lines[last_line_index]
        if not (re.search('\n',last_line)):
            ignored_file_add_newline = True
            ignored_file_lines[last_line_index] = last_line + '\n'
    
    with open(queue_file, encoding="utf8") as file:
        queue_file_lines = file.readlines()
        line_num = 0
        for line in queue_file_lines:
            if not (re.search('(^#|^$)',line)):
                queue_line_found = re.search('.*:(mixer|twitch|youtube|facebook|twitter|dlive|mobcrush) {1}"[a-hj-np-yA-HJ-NP-Y0-9]{3}[- ][a-hj-np-yA-HJ-NP-Y0-9]{3}[- ][a-hj-np-yA-HJ-NP-Y0-9]{3}"',line)
                if (queue_line_found):
                    course_id = format_course_id(get_value_from_cfg_line(line))
                    user_info_string = re.sub(' {1}"[a-hj-np-yA-HJ-NP-Y0-9]{3}[- ][a-hj-np-yA-HJ-NP-Y0-9]{3}[- ][a-hj-np-yA-HJ-NP-Y0-9]{3}"|\n','',line)
                    queue_course_id[user_info_string] = course_id
                    queue_line_index[user_info_string] = line_num
                    queue_list.append(user_info_string)
                    queue_position[user_info_string] = len(queue_list)
            line_num += 1
        last_line_index = len(queue_file_lines) - 1
        if (last_line_index >= 0):
            last_line = queue_file_lines[last_line_index]
            if not (re.search('\n',last_line)):
                queue_file_add_newline = True
                queue_file_lines[last_line_index] = last_line + '\n'
            
    print(str(queue_list))
            
    with open(commands_file, encoding="utf8") as file:
        command_file_lines = file.readlines()
        for line in command_file_lines:
            value = get_value_from_cfg_line(line)
            if not (value == '' or value == []):
                command_found = re.search('.*:',line)
                if (command_found):
                    command_name = command_found.group(0)
                    command_name = re.sub(':','',command_name)
                    if not (command_name == ''):
                        commands[command_name] = value

                commands_list.append(value)
                
    print("Commands List: " + str(commands_list))
    commands_count = len(commands_list)
    cmd_index = 0
    for command in commands_list:
        if (cmd_index == 0):
            commands_re = command
            commands_string = command
        else:
            commands_re = commands_re + '($|\s)|' + command
            commands_string = commands_string + " " + command
            
        if (cmd_index == commands_count - 1):
            commands_re = commands_re + '($|\s)'
        cmd_index += 1
        
    sock = socket.socket()
    sock.connect((config['server'], int(config['port'])))
    sock.send(f"PASS {config['oauth']}\r\n".encode('utf-8'))
    sock.send(f"NICK {config['bot_name']}\r\n".encode('utf-8'))
    sock.send(f"JOIN #{config['streamer_name']}\r\n".encode('utf-8'))

    CHAT_MSG = re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :")
    
    try:
        while True:
            resp = sock.recv(2048).decode('utf-8')

            if resp.startswith('PING'):
                # sock.send("PONG :tmi.twitch.tv\n".encode('utf-8'))
                sock.send("PONG\n".encode('utf-8'))
            elif len(resp) > 0:
                username = re.search(r"\w+", resp).group(0)  # return the entire match
                message = CHAT_MSG.sub("", resp)
                
                if not (is_ignored_user(username, message)):
                    parsed_command = command_in_message(message)
                    if (parsed_command[0] == True):
                        if (parsed_command[1] == commands['open_queue']):
                            if (is_admin(username)):
                                queue_is_open = True
                                chat('The queue is now open for submissions!')
                                
                        if (parsed_command[1] == commands['close_queue']):
                            if (is_admin(username)):
                                queue_is_open = False
                                chat('The queue is now closed and not accepting any more submissions!')
                        
                        if (parsed_command[1] == commands['add_course']):
                            chat(add_course_from_message(username, message))
                        
                        if (parsed_command[1] == commands['show_queue_count']):
                            chat('The queue currently has ' + str(len(queue_list)) + ' course(s)')
                    
                        if (parsed_command[1] == commands['clear_queue']):
                            if (is_admin(username)):
                                chat(clear_queue())
                    
                        if (parsed_command[1] == commands['win_course']):
                            if (is_admin(username)):
                                if (len(queue_list) > 0):
                                    user_info_string = queue_list[0]
                                    user_info = convert_value_to_user_info(user_info_string)
                                    course_id = queue_course_id[user_info_string]
                                    remove_course(1)
                                    chat(user_info[0] + " from " + user_info[1] + ": your course " + course_id + " has been beaten!" + " | " + next_course())
                                else:
                                    chat("There is no active course to win...")
                    
                        if (parsed_command[1] == commands['lose_course']):
                            if (is_admin(username)):
                                if (len(queue_list) > 0):
                                    user_info_string = queue_list[0]
                                    user_info = convert_value_to_user_info(user_info_string)
                                    course_id = queue_course_id[user_info_string]
                                    remove_course(1)
                                    chat(user_info[0] + " from " + user_info[1] + ": your course " + course_id + " is victorious!" + " | " + next_course())
                                else:
                                    chat("There is no active course to lose...")
                                
                        if (parsed_command[1] == commands['show_position_in_queue']):
                            user_info = get_user_info(username, message)
                            user_info_string = convert_user_info_to_string(user_info)
                            if user_info_string in queue_position:
                                position = queue_position[user_info_string]
                                if (position == 1):
                                    chat(user_info[0] + " from " + user_info[1] + " your course is up next/being played now!")
                                else:
                                    chat(user_info[0] + " from " + user_info[1] + " you are in position " + str(position))
                            else:
                                chat(user_info[0] + " from " + user_info[1] + " you are not entered into the queue!")
                        
                        if (parsed_command[1] == commands['show_queue_list']):
                            chat(get_full_queue())
                    
                        if (parsed_command[1] == commands['show_current_course']):
                            if (len(queue_list) > 0):
                                user_info = convert_value_to_user_info(queue_list[0])
                                chat("The current course is " + queue_course_id[queue_list[0]] + " by " + user_info[0] + " from " + user_info[1])
                            else:
                                chat(empty_queue_message())
                    
                        if (parsed_command[1] == commands['skip_course']):
                            if (is_admin(username)):
                                chat(skip_current_course())
                            
                        if (parsed_command[1] == commands['move_course_to_end']):
                            if (is_admin(username)):
                                chat(move_course_to_end())
                        
                        if (parsed_command[1] == commands['remove_course']):
                            if (is_admin(username)):
                                if (len(queue_list) > 0):
                                    msg = remove_course(1)
                                    chat(msg + " " + next_course())
                                else:
                                    chat("There is no active course to remove...")
                                    
                        if (parsed_command[1] == commands['exchange_course']):
                            chat(exchange_course(username, message))
                        
                        if (parsed_command[1] == commands['show_commands']):
                            chat(show_user_commands())
                            
                        if (parsed_command[1] == commands['leave_queue']):
                            chat(leave_queue(username, message))
                            
                        if (parsed_command[1] == commands['ignore_user']):
                            if (is_admin(username)):
                                chat(ignore_user(message))
                        
                        if (parsed_command[1] == commands['unignore_user']):
                            if (is_admin(username)):
                                chat(unignore_user(message))
                                
                        if (parsed_command[1] == commands['toggle_debug_mode']):
                            if (is_admin(username)):
                                chat(toggle_debug_mode())
                        
                        if (parsed_command[1] == commands['song_request']):
                            msg = request_song(username, message)
                            if not (msg == ''):
                                chat(msg)
    except KeyboardInterrupt:
        sock.close()
        exit()

if __name__ == '__main__':
    main()