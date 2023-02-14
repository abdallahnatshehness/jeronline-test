import os
import sys
import socket
import platform

auto_depot_path = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir))
utilities_folder = os.path.join(auto_depot_path, 'utilities')

hour_format = '%H:%M:%S'
date_format = '%d-%b-%Y'
time_format = '%d-%m-%y_%H-%M'  # This format is used in file and folder names
pretty_time_format = '%d/%m/%y %H:%M'
full_time_format = '%d-%b-%Y %H:%M:%S'

if sys.platform == 'darwin':
    current_os = 'Mac'
    applications_exec = '.app'
    temp_folder = '/tmp'
    platform_machine = 'Mac'
    if 'RELEASE_ARM64' in platform.uname().version:
        platform_machine = 'ARM'
elif sys.platform == 'win32' and platform.architecture()[0] == '64bit':
    current_os = 'Win'
    try:
        is_windows_11 = sys.getwindowsversion().build > 20000
    except:
        is_windows_11 = False
    applications_exec = '.exe'
    trash_path = os.path.join('C:\$Recycle.Bin')
    temp_folder = os.environ['TMP']
    platform_machine = 'Win'
else:
    current_os = 'Linux'
    platform_machine = 'Linux'

client_name = socket.gethostname().replace('.local', '')
user_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
user_download = os.path.join(os.path.expanduser('~'), 'Downloads')
allure_utils_path = os.path.join(utilities_folder, 'allure')
if current_os == 'Win':
    local_allure_executable = os.path.join(allure_utils_path, 'bin', 'allure.bat')
else:
    local_allure_executable = os.path.join(allure_utils_path, 'bin', 'allure')

language = {
    'שם פרטי': {'ar': 'الاسم الشخصي', 'he': 'שם פרטי'},
    'שם משפחה': {'ar': 'اسم العائلة', 'he': 'שם משפחה'},
    'סוג זיהוי': {'ar': 'نوع الهوية', 'he': 'סוג זיהוי'},
    'מספר ת.ז.': {'ar': 'رقم الهوية', 'he': 'מספר ת.ז.'},
    'מספר דרכון': {'ar': 'رقم جواز السفر', 'he': 'מספר דרכון'},
    'טלפון נייד': {'ar': 'هاتف محمول', 'he': 'טלפון נייד'},
    'טלפון קווי': {'ar': 'هاتف', 'he': 'טלפון קווי'},
    'דוא"ל': {'ar': 'البريد الالكتروني', 'he': 'דוא"ל'},
    'יישוב': {'ar': 'المدينة', 'he': 'יישוב'},
    'רחוב': {'ar': 'شارع', 'he': 'רחוב'},
    'מספר בית': {'ar': 'رقم البيت', 'he': 'מספר בית'},
    'מיקוד': {'ar': 'الرمز البريدي', 'he': 'מיקוד'}
}
err_msgs = {'empty_value':'שדה חובה',
            'invalid_email':'שדה לא תקין',
            'invalid_text':'יש להזין אותיות בעברית בלבד ותווים מיוחדים',
            'invalid_id' : 'מספר זהות לא תקין',
            'numbers_only':'יש להזין ספרות בלבד',
            'full_numbers':'יש להשלים את הספרות החסרות',
}