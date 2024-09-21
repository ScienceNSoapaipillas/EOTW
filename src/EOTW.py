# -*- coding: utf-8 -*-
"""
Created on Sat Sep  7 03:09:15 2024

@author: Sci
"""

# standard imports
import requests
import json
import time
import sys
import pytz
from datetime import datetime
import re

# special import
import pandas as pd



class EOTW:
    
    def __init__(self, activity=None, end_time=None):
        
        url         = f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.json?player=i_do_science"
        headers     = {"Accept": "application/json"}
        response    = requests.get(url, headers=headers)
        data        = self._reformat_json_(response.json())
        
                
        skillsU = ["Overall", "Attack", "Defence", "Strength", "Hitpoints", "Ranged", "Prayer", 
          "Magic", "Cooking", "Woodcutting", "Fletching", "Fishing", "Firemaking", 
          "Crafting", "Smithing", "Mining", "Herblore", "Agility", "Thieving", "Slayer", 
          "Farming", "Runecrafting", "Hunter", "Construction"]
        skills = [x.lower() for x in skillsU]
        bosses = [x.lower() for x in list(set(list(data.keys())) - set(skills))]
        
        
        if activity.lower() in skills:
            self.headers       = ['Name', 'Levels Gained', 'XP Gained', 'Buy in (k)', 'Balance (M)', 'XP Start', 'Level Start', 'Time Zone', 'Last Updated']
            self.activity_type = 'skills'
        elif activity.lower() in bosses:
            self.headers       = headers = ['Name', 'Kc Gained', 'Buy in (k)', 'Balance (M)', 'Kc Start', 'Time Zone', 'Last Updated']
            self.activity_type = 'activities'
        
        self.table = pd.DataFrame(columns = self.headers)
        self.skills   = skills
        self.bosses   = bosses
        self.activity = activity.lower()
        self.url      = 'https://secure.runescape.com/m=hiscore_oldschool/index_lite.json?player='
        self.end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        #self.table    = 0
        return        


    def _reformat_json_(self, json_data):
        better_json = {}
        
        # Reformat the 'skills' entries
        for entry in json_data['skills']:
            better_json[entry['name'].lower()] = [entry['level'], entry['xp']]
            
        # Reformat the 'activities' entries
        for entry in json_data['activities']:
            better_json[entry['name'].lower()] = entry['score']
    
        return better_json
  
    
    def _convert_to_integer_(self, value: str) -> int:
        # Remove commas and spaces
        value = str(value).replace(',', '').replace(' ', '')
        
        # Handle suffixes for thousands (K/k) and millions (M/m)
        if re.match(r'^\d+(\.\d+)?[Kk]$', value):
            # Convert '250k' or '250K' to integer
            return int(float(value[:-1]) * 1_000)
        elif re.match(r'^\d+(\.\d+)?[Mm]$', value):
            # Convert '0.25M' or '0.25m' to integer
            return int(float(value[:-1]) * 1_000_000)
        else:
            # Try converting directly to integer if no suffix
            try:
                return int(float(value))
            except ValueError:
                raise ValueError(f"Cannot convert {value} to an integer.")
    
    
    def get_player_info(self, player):
            
        activity = self.activity
        
        #print(player)
        
        if type(player) == dict:
            #print('1')
            name             = player.get('name', 'Null')
            player_timezone  = player.get('time', 'Null')
            player_wager     = round(self._convert_to_integer_(player.get('buyin', 0))/1e3, 3)
            carry_over       = round(self._convert_to_integer_(player.get('carry over', 0))/1e6, 3)
            
        elif type(player) == str and player.count(',') == 0:
           # print('2')
            name             = player
            player_timezone  = 0
            player_wager     = 0
            carry_over       = 0
            # 'I do science, America/Denver, 250k'
            
        elif type(player) == str and player.count(',') >= 2:
            #print('3')
            data = player.split(',')
            
            if len(data) < 3:
                print('WARNING: {player} is not good input data. I need more specific info or a reformatting!')
                print('These need to be: user_name, time zone, buyin fee, rollover/accumulation (optional)')
                print(f'Example inputs: "I Do Science, America/Denver, 250k"')
                print(f'Example inputs: "66_q_p, MST, 5m, 12m"')
                print('')
                print(f'You can also drag and drop a .txt or .csv file in here and I can understand it!')
                
            
            nospace_data  = [x[1:] if x[0] == ' ' else x for x in data]
            #print(nospace_data)
            
        
            if len(nospace_data) == 3:
                name, player_timezone, player_wager  = nospace_data
                carry_over = 0
                
            elif len(nospace_data) == 4:
                name, player_timezone, player_wager, carry_over = nospace_data
                             
            player_wager = round(self._convert_to_integer_(player_wager)/1e3, 3)
            carry_over   = round(self._convert_to_integer_(carry_over)/1e6, 3)
            
            
        
        # start parsing and generating input data
        player_name = name.replace(' ','_').lower()
        url         = f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.json?player={player_name}"
        headers     = {"Accept": "application/json"}
        response    = requests.get(url, headers=headers)
        data        = self._reformat_json_(response.json())
        tracked     = data[activity.lower()]
        last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z%z').strip()
        
        if self.activity_type == 'activities':
            if tracked == -1 or tracked == '-1':
                tracked = 0
            out = {'Name': name, 'Buy in': player_wager, 'Carry Over Balance': carry_over, 
                   'Current Kc': tracked, 'last_update': last_update, 'Time Zone': player_timezone}
        elif self.activity_type == 'skills':
            out = {'Name': name, 'Buy in': player_wager, 'Carry Over Balance': carry_over, 
                   'Current Level': tracked[0], 'Current XP': tracked[1], 'last_update': last_update, 'Time Zone': player_timezone}
    
        return out
    


    def add_to_table(self, player):

        # Get player info based on the activity
        info = self.get_player_info(player)
        
        name = info['Name']
        
        #print(player)
        #print(name)
        
        # Check if the player is already in the DataFrame
        if name in self.table['Name'].to_list():
            print(f'Warning! I see {name} in the table already. Remove this person if you need to add them, or create a new table.')
            return self.table
        
        # Create a dictionary with the data to be added, initialize with 0 for missing data
        row_data = {header: info.get(header, 0) for header in self.headers}
        
        
        row_data['Name']          = name
        row_data['Buy in (k)']    = info['Buy in']
        row_data['Balance (M)']   = info['Carry Over Balance']
        row_data['Time Zone']     = info['Time Zone']
        row_data['Last Updated']  = info['last_update']
            
        # Fill in specific fields for skills-related activities
        if self.activity_type == 'skills':
            row_data['Levels Gained']      = int(0)
            row_data['XP Gained']          = int(0)
            row_data['XP Start']           = info['Current XP']
            row_data['Level Start']        = info['Current Level']
        
        elif self.activity_type == 'activities':
            row_data['Kc Gained'] = 0
            row_data['Kc Start']  = info['Current Kc']

                 
        # Create a new DataFrame for the new row and add it to the existing DataFrame
        new_row    = pd.DataFrame([row_data], columns=self.headers)
        self.table = pd.concat([self.table, new_row], ignore_index=True)
        return


    def remove_from_table(self, name):
        self.table = self.table[self.table['Name'].str.lower().str.replace(' ', '_') != name.lower().replace(' ', '_')]
        return
    
    
   
    def update_table(self):
        
        to_update = self.table['Name'].to_list()
        
        
        for name in to_update:
            table_info = self.table[self.table['Name'] == name] 
            info       = self.get_player_info(name)
            
            
            if self.activity_type == 'skills':
        
                if table_info['XP Start'].values[0] != info['Current XP']:
                    self.table.loc[self.table['Name'] == name, 'XP Gained']     = info['Current XP'] - table_info['XP Start'].values[0]
                    self.table.loc[self.table['Name'] == name, 'Levels Gained'] = info['Current Level'] - table_info['Level Start'].values[0]
                    self.table = self.table.sort_values(by='XP Gained', ascending=False)
                    
                else:
                    self.table.loc[self.table['Name'] == name, 'Last Updated'] = info['last_update']
            
            if self.activity_type == 'activities':        
                if table_info['Kc Start'].values[0] != info['Current Kc']:
                    self.table.loc[self.table['Name'] == name, 'Kc Gained']     = info['Current Kc'] - table_info['Kc Start'].values[0]
                    self.table = self.table.sort_values(by='Kc Gained', ascending=False) 
                    
                else:
                    self.table.loc[self.table['Name'] == name, 'Last Updated'] = info['last_update']
        #self.table.to_csv(f'{self.activity}_{self.stop_date}.csv', index=False)

        return
   

    def jackpot(self):
        if type(self.table) != int:
            total = str(round(self.table['Buy in (k)'].sum()/1e3, 3)) + ' mill'
        else:
            total = 0             
        return total
                
    def rules(self):
        activity      = self.activity
        activity_type = self.activity_type
        end_time      = self.end_time.strftime('%Y-%m-%d %H:%M')
        
        total = self.jackpot()       
 
        if activity_type == 'skills':
            eotw  = 'SOTW'
            buyin = '250k'
            late  = '1M'
            act   = 'skill'
        elif activity_type == 'activities':
            eotw  = 'BOTW'
            buyin = '500k'
            late  = '2M'
            act   = 'boss'
        
        out = '' 
        out += f'Hello! And welcome to {eotw}! I am a bot with rules written as a friendly reminder. I am here to answer some FAQs'
        out += '\n## What is the current competition?'
        out += f'\nCurrently, we are doing {activity.title()}. The current prize pool is {total}'
        out += f'\n## When does this {eotw} end?'
        out += f'\nIt ends {end_time} (format is year - month - day  24-hour:minute). For example, "2024-09-13 18:00" reads September 13, 2024, at 6 PM.'
        out += '\n## When is late buy in? When can I buy in late?'
        out += f'\nLate buy in is {late}, and can be done any time after the {act} wheel is spun. You are responsible for communicating with the CEO of {eotw} for getting this in on time!'
        out += '\netc.. etc.. etc..'

        '''
        print(f'Hello! And welcome to {eotw}! I am a bot with rules written as a friendly reminder. I am here to answer some FAQs')
        print('\nWhat is the current competition?')
        print(f'Currently, we are doing {activity.title()}. The current prize pool is {total}\n')
        print(f'When does this {eotw} end?')
        print(f'It ends {end_time} (format is year - month - day  24-hour:minute). For example, "2024-09-13 18:00" reads September 13, 2024, at 6 PM.')
        print('\nWhen is late buy in? When can I buy in late?')
        print(f'Late buy in is {late}, and can be done any time after the {act} wheel is spun. You are responsible for communicating with the CEO of {eotw} for getting this in on time!')
        print('etc.. etc.. etc..')
        '''
        return out
    
    
    def sugma(self):
        print('Ninja says fuck you read the rules')
        return 'Ninja says fuck you read the rules'
         
         
         
         
    
