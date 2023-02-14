import csv
from pathlib import Path

import yaml
from behave import *
import sys, os
import time
import psutil


from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.common import exceptions

from utils.managers.infra import local_server_manager

script_folder = os.path.dirname(__file__)
sys.path.append(os.path.join(script_folder, os.pardir, os.pardir, os.pardir, 'Packages'))
sys.path.append(os.path.join(script_folder, os.pardir, os.pardir, os.pardir, 'Infra_testing', 'central_testing'))
sys.path.append(os.path.join(script_folder, os.pardir, os.pardir, os.pardir, 'Scripts'))

from utils import central_utils, files_utils, sub_process, misc_utils, plugin_info
from infra import config, reporter, logger
from apps.audio_apps.waves_static_utils import WavesStaticUtils as WSU
from apps.base_apps import process, chrome_driver

sys.path.append(os.path.join(script_folder, os.pardir, os.pardir, 'Scripts'))
from infra import custom_exceptions as ce

log = logger.get_logger(__name__)
rep = reporter.get_reporter()

use_step_matcher("parse")


@given("I install Waves Central from Auto Update folder")
def install_dummy_waves_central(context):
    """This test works with Central from nightly that have an additional installer called auto-updater with a dummy version 0.0.1
    when this early version starts, the update service return update exists and the update happens.
    we can test earlier versions with --no-autoupdate argument in Central"""
    central_utils.create_central_json_prefs()
    installer_pattern = 'Autoupdate/*0.0.1*'
    installer_extension = {'Win': '.exe', 'Mac': '.dmg'}[config.current_os]
    path_to_central_in_bm = installer_pattern + installer_extension
    dummy_path = sorted(Path(context.opt_dict['central_path']).rglob(path_to_central_in_bm))[0]
    log.debug(f'Path to Autoupdate: {dummy_path}')
    central_utils.install_from_path(dummy_path)
    if config.current_os == 'Mac':
        os.system(f"open '{config.central_path}'")
    else:
        os.system(f'"{config.central_exec}"')
    p = process.Process(os.path.split(config.central_exec)[-1])
    wait_for_process_to_keep_up_or_down(p, up=False)
    if config.current_os == 'Mac':
        wait_for_process_to_keep_up_or_down(p)
        wait_for_process_to_keep_up_or_down(p, up=False)
    log.info('Central still UP & Update are done')

@given("I install Waves Central from installer")
def install_waves_central(context):
    central_utils.create_central_json_prefs()
    installer_pattern = {'Win': 'Waves Central Setup*[!-0.0.1-]*.exe',
                         'Mac': 'Waves Central*[!-0.0.1-]*universal.dmg'
                         }[config.current_os]
    installer_path = sorted(Path(context.opt_dict['central_path']).rglob(installer_pattern))[0]
    log.debug(f'Path to installer: {installer_path}')
    central_utils.install_from_path(installer_path)


@then("Central resources should be signed")
def verify_sign(context):
    not_sign = []
    if config.current_os == 'Win':
        files_to_verify = ['instl-V9.exe', 'instl-V10.exe', 'instl.exe', 'wle.exe', 'who_locks_file.dll']
        for f in files_to_verify:
            file_full_path = sorted(Path(config.central_path).rglob(f))[0]
            if not misc_utils.verify_signature(file_full_path)[0]:
                not_sign.append(file_full_path)
        if not_sign:
            rep.add_label_to_step('Not Signed', '\n'.join(*not_sign))
            raise AssertionError('Not All Files are signed')
    else:
        ret_val = misc_utils.verify_signature(Path(config.central_path))
        if not ret_val[0]:
            rep.add_label_to_step('Not Signed', ret_val[1])

def wait_for_process_to_keep_up_or_down(process, up=True, timeout=9000):
    i = 0
    condition_to_check = True
    while condition_to_check:
        if up:
            condition_to_check = process.is_process_running()
        else:
            condition_to_check = not process.is_process_running()
        log.info(f'{process.process_name} run status still {up}')
        time.sleep(.1)
        i += 1
        if i > timeout:
            raise ce.WERunTimeError(f'Timeout while waiting for {process.process_name} status to be {up}')


@Then('Installed Waves Central version must be different than "{version}"')
def waves_version_compare(context, version='0.0.1'):
    if config.current_os == 'Win':
        current_version = WSU.get_version_from_dll_win(os.path.join(config.central_exec), ver_fields=3)
        path_from_bm = os.path.join(context.opt_dict['central_path'], 'Apps', 'Central', 'win-unpacked',
                                    'Waves Central.exe')
        version_same_build = WSU.get_version_from_dll_win(path_from_bm, ver_fields=3)
    else:
        current_version = WSU.get_version_from_info_plist(
            os.path.abspath(os.path.join(config.central_path, 'Contents', 'Info.plist')),
            version_type='short')
        path_from_bm = central_utils.find_central_app(context.opt_dict['central_path'])[0]
        version_same_build = WSU.get_version_from_info_plist(
            os.path.abspath(os.path.join(path_from_bm, 'Contents', 'Info.plist')),
            version_type='short')

    rep.add_label_to_step('current installed version', current_version)
    rep.add_label_to_step('version of the same build', version_same_build)
    if current_version <= version:
        raise AssertionError('Waves Central does not updated')
    elif current_version != version_same_build:
        rep.add_label_to_step('WARNING', 'Central updated but not to same build version')


@When('I get back my Waves Central')
def return_old_central(context):
    process.kill_processes("Waves Central", "WavesLocalServer")
    handle_user_dialog(context, 'stop')
    time.sleep(5)
    try:
        files_utils.bring_back(config.central_path, apass=context.apass)
    except Exception as e:
        log.info(e)
        files_utils.bring_back(config.central_path, apass=context.apass)

@Given('Waves Central "{version}" is installed')
def install_central_custom_version(context, version):
    version = '.'.join(version.split('.')[:3]) # version should have only two dots
    if not os.path.exists(config.central_exec):
        current_version = '0.0.0'
    else:
        if config.current_os == 'Win':
            current_version = WSU.get_version_from_dll(config.central_exec, 'short')
        else:
            current_version = WSU.get_version_from_info_plist(os.path.join(config.central_path, 'Contents', 'info.plist'), 'short')
    current_version = '.'.join(current_version.split('.')[:3])
    log.info(f'current version: {current_version}')
    if current_version != version:
        uninstall_central_app()
        install_version(version)


@Given('Latest Waves Central is installed')
def install_central_latest_version(context):
    install_version(version='latest')


def uninstall_central_app():
    """Uninstall Central on windows copy it for backup and try to uninstall
    in mac, simply move aside"""
    if config.current_os == 'Win':

        if Path(config.central_path).exists():
            files_utils.copy_anything(config.central_path, config.central_path+'_old')
        uninstall_exec = Path(config.central_path).joinpath('Uninstall Waves Central.exe')
        if uninstall_exec.exists():
            try:
                sub_process.sub_popen(uninstall_exec, '/allusers','/S', timeout=300)
                return
            except ce.WERunTimeError:
                log.warning('Uninstall was not found, remove Central registry key and delete Central folder instead')

        # in case the uninstall failed or not exists - remove central folder and delete reg key
        key = r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{ab507e17-892b-5203-838d-d58d8d09c50f}'
        files_utils.remove_paths(config.central_path)
        try:
            sub_process.sub_popen('Reg', 'delete', key, '/f')
        except ce.WERunTimeError as e:  # nothing to remove
            pass

    else:  # Mac
        files_utils.move_aside(config.central_path)

def install_version(version):
    if config.current_os == 'Win':
        central_installer_folder = Path('//gimli/online_installers/Waves Central')
        ext = 'exe'
    else:
        central_installer_folder = Path(config.user_desktop, 'Automation', f'central_installers_mount')
        mount_path = 'gimli/online_installers/Waves Central'
        misc_utils.mount_server('smb', mount_path, str(central_installer_folder),
                                user_credentials='uautomation:_AutoUser1_')
        ext = 'dmg'

    if version == 'latest':
        central_installer_folder = list(central_installer_folder.glob('[!Old Updates]*'))[0]
    else:
        central_installer_folder = central_installer_folder.joinpath('Old Uploads', f'V{version}')

    installer_name = 'Install_Waves_Central'
    exec_name = '%s.%s' % (installer_name, ext)

    if config.current_os == 'Win':
        installer_exec = central_installer_folder.joinpath(exec_name)
        sub_process.sub_popen(installer_exec, '/S', '/F', timeout=300)

    elif config.current_os == 'Mac':
        installer_exec = central_installer_folder.joinpath(exec_name)
        dmg_temp = os.path.join(config.temp_folder, 'central')
        misc_utils.mount_dmg(dmg_temp, installer_exec)
        files_utils.copy_ditto(os.path.join(dmg_temp, os.path.basename(config.central_path)), config.central_path, timeout=120)


@Given('Central environment is cleaned')
def clean_central_environment(context):
    userPWD = context.apass
    context._config.userPWD = userPWD

    context._config.last_installed_plugin = ''
    context._config.last_installed_plugin_version = ''
    server_man = local_server_manager.WavesLocalServer()
    server_man.stop()
    log.debug([proc.name() for proc in psutil.process_iter()])
    central_utils.clean_central(userPWD)
    delete_sample_libraries(context)

@Given('Sample libraries shortcuts are deleted')
def delete_sample_libraries(context):
    try:
        files_utils.unlink_all_sample_libraries()
    except FileNotFoundError as e:
        log.warning('No sample libraries were founded')

@When("I launch Waves Central")
def launch_waves_central(context):
    context._config.central = context.om.create_objects(['Waves Central'])
    central = context._config.central

    try:
        handle_user_dialog(context, 'start')
        central.launch()
        central.wait_for_welcome_dialog()
    except TimeoutException as e:
        context.user_data['img_path'] = central.screen_cap(os.path.join(context.report_path, 'exception_screenshot'),
                                                           crop_to_window=False)
        raise e
    finally:
        handle_user_dialog(context, 'stop')

    context._config.timing_histories_file = {}
    context._config.timing_summary_step = {}
    context._config.phase_number = {}

@When('I "{mode}" handle user dialog')
def handle_user_dialog(context, mode='start'):
    if config.current_os != 'Mac':
        return
    if mode == 'start' and not context.om.apps.get('central_dialog_handler', False):
        userPWD = context.apass
        context._config.userPWD = userPWD
        if config.current_os == 'Mac':
            from multiprocessing import Process as p
            from apps.audio_apps.base_audio_app import handle_dialogs
            context._config.dialog_handler = p(target=handle_dialogs,
                                               kwargs={'handle_list': ['handle_security_agent'], 'password': userPWD})
            context._config.dialog_handler.start()
            context.om.apps['central_dialog_handler'] = context._config.dialog_handler
    elif mode == 'stop' and context.om.apps.get('central_dialog_handler', False):
        log.info('terminating handle_security_agent')
        context._config.dialog_handler.terminate()
        del context.om.apps['central_dialog_handler']

@when("I sign in Central")
def central_sign_in(context):
    central = context._config.central
    central.set_current_page(central.page_object.WelcomeDialog())
    central.switch_to.active_element

    widget_login = central.current_page.widgets['Login']
    central.page_object.Button(central.find_widget(widget_login)).click()

    central.set_current_page(central.page_object.LoginDialog())
    widget = central.current_page.widgets['login_url']
    login_element = central.find_widget(widget)
    login_url = login_element.get_attribute('data-login-token')
    browser_driver = chrome_driver.ChromeDriver()
    browser_driver.login_to_waves(login_url, context.central_user, context.central_pass)
    browser_driver.minimize_window()
    wait_for_sync_dialog(context)
    browser_driver.quit()
    if config.current_os == 'Mac':
        chorme_proc_name = 'Google Chrome'
    else:
        chorme_proc_name = 'chrome'
    process.kill_processes(chorme_proc_name)

@When("I wait for sync dialog to disappear")
def wait_for_sync_dialog(context):
    central = context._config.central
    central.set_current_page(central.page_object.ProgressDialog())
    widget = central.current_page.widgets['Progress Bar']
    central.wait_until((ec.visibility_of_element_located((widget['Locator']))))
    central.wait_until(ec.invisibility_of_element((widget['Locator'])))
    central.wait_until(central.process_status_block)

@when("I close Waves Central")
def central_close_app(context):
    handle_user_dialog(context, 'stop')
    context._config.central.tear_down()

    for history_file in context._config.timing_histories_file.keys():
        with open(history_file, 'a') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(context._config.timing_histories_file[history_file])
        rep.add_excel_file_as_link_to_step(history_file, file_name=Path(history_file).stem)

    if hasattr(context, 'need_to_move_central_aside') and context.need_to_move_central_aside:
        files_utils.bring_back(config.central_path, apass=context._config.userPWD)


@when("I summarize this Central run")
def summarize_run(context):
    columns = [('total', 'Total Time'), ('sync', 'Sync'), ('copy', 'Copy'), ('post', 'Post')]
    for product_name, phases_timings in context._config.timing_summary_step.items():
        rep.add_table(f'Timing Summary for {product_name}',
                      caption=f'Timing Summary for {product_name}', type='iterable')
        rep.add_columns(f'Timing Summary for {product_name}', *columns)
        for phase in phases_timings:
            rep.add_row(f'Timing Summary for {product_name}'
                        , [phase['total'], phase['sync'], phase['copy'], phase['post']])

        rep.add_table_to_step(f'Timing Summary for {product_name}')


@when('I click on "{element_name}" on Waves Central')
def click_on_element(context, element_name):
    central = context._config.central
    if element_name == 'Current OS':
        element_name = {'Win': 'Windows'}.get(config.current_os, 'Mac')
        widget = central.current_page.select_os_target(element_name)
    else:
        widget = central.current_page.widgets[element_name]
    central.wait_until(ec.element_to_be_clickable(widget['Locator']))
    central.page_object.Button(central.find_widget(widget)).click()


@when('I write "{word}" into "{element}" text field on Waves Central')
def write_into_field(context, word, element):
    central = context._config.central
    widget = central.current_page.widgets[element]
    time.sleep(1)
    central.page_object.TextField(central.find_widget(widget)).clear()
    central.page_object.TextField(central.find_widget(widget)).set_text(word)


@when('I search and check these products from the products list on Waves Central')
def search_check_products_table(context):
    for row in context.table:
        context.execute_steps(u"""
                        When I write "{word}" into "{element}" text field on Waves Central
                        """.format(word=row['Name'], element='Search'))
        context.execute_steps(u"""
                                When I check "{product_name}" of "{version}" from products list
                                """.format(product_name=row['Name'], version=row['Version']))


@Then('I verify that the product "{product}" is in the update list')
def product_in_update_list(context, product):
    central = context._config.central
    context.execute_steps(u"""When I select "Install Products" from Waves Central navigation menu""")
    widget = central.current_page.widgets['All Products']
    central.page_object.Button(central.find_widget(widget)).click()
    widget = central.current_page.widgets['updates available']
    central.page_object.Button(central.find_widget(widget)).click()
    widget = central.current_page.widgets['update details']
    central.wait_until(ec.element_to_be_clickable(widget['Locator']), timeout=1800)
    central.page_object.Button(central.find_widget(widget)).click()
    widget = central.current_page.widgets['update products list']
    update_items = central.page_object.Table(central.find_widgets(widget), widget['table'])
    product_found = False
    for item in update_items:
        if item['label'].get_text in product:
            product_found = True
            break
    if not product_found:
        raise AssertionError(f'{product} is not included in items for update')
    from_version, to_version = item['details'].get_text.split(' > ')
    context.user_data[f'latest_version'] = to_version


@Then('I verify that "{product_name}" is updated in version "{maj_version}"')
def verify_update(context, product_name, maj_version):
    """Get the version from xml, compare it to what we keep in user_data['latest_version']"""
    plugins = plugin_info.find_xml_info([str(Path(config.main_waves_path, f'Plug-Ins V{maj_version}'))])
    plugin = [p for p in plugins if p.product_name == product_name]
    plugin_version = plugin[0].version.split(' ')[0]
    if plugin_version != context.user_data['latest_version']:
        raise AssertionError(f'{product_name} is not at latest version')


@when('I select "{menu_item}" from Waves Central navigation menu')
def choose_from_nav(context, menu_item):
    central = context._config.central
    central.set_current_page(central.page_object.NavigationBar())
    widget = central.current_page.widgets[menu_item]
    central.page_object.Button(central.find_widget(widget)).click()
    context.last_used_page = central.current_page.page_factory[menu_item]
    central.set_current_page(context.last_used_page)


@When('I choose the offline package "{path_to_package}"')
def choose_offline_package(context, path_to_package):
    select_path_system_dialog(context, path_to_package)


@When('I choose path "{path_to_package}" from system dialog')
def select_path_system_dialog(context, path_to_package):
    if config.current_os == 'Mac':
        central = context._config.central
        current_mouse_pos = central.mouse.position
        central.set_clipboard(path_to_package)
        central.process_name = 'Waves Central'
        pos = central.get_win_position()
        central.click_mouse(*pos)
        time.sleep(5)
        central.keystroke('g', modifiers=['primary', 'shift'], sleep_time=0.2)
        central.keystroke(central.get_clipboard())
        time.sleep(5)
        central.press_enter(5)
        central.press_enter()
        central.move_mouse(*current_mouse_pos)
    else:
        raise ce.WENotImplementedError('this function is not ready yet for windows')


@when('I search in view "{version}"')
def search_in_view(context, version):
    central = context._config.central
    widget = central.current_page.widgets['Products Filter Expand']
    central.page_object.DropDown(central.find_widget(widget)).click()
    widget = central.current_page.widgets['Products Filter']
    checkboxes = central.page_object.DropDown(central.find_widget(widget)).get_all_items
    for checkbox in checkboxes:
        checkbox.check()


@when('I wait until "{element_name}" button appeared with message "{expected_msg}"')
def wait_for_button(context, element_name, expected_msg):
    import platform
    central = context._config.central
    if config.current_os == 'Mac' and platform.mac_ver()[0] < '10.12.6':
        # load alert window and click on Continue
        central.set_current_page(central.page_object.UnSupportedOS())
        widget = central.current_page.widgets['Continue']
        central.page_object.Button(central.find_widget(widget)).click()
    central.set_current_page(central.page_object.ProgressDialog())
    widget = central.current_page.widgets[element_name]
    try:
        handle_user_dialog(context)
        central.wait_until(ec.element_to_be_clickable(widget['Locator']), timeout=1800)
    except exceptions.TimeoutException as e:
        context.user_data['img_path'] = central.screen_cap(os.path.join(context.report_path, 'timeout_screenshot'),
                                                           crop_to_window=False)
        log.error(f'Timeout: {e}')
        raise
    else:
        widget = central.current_page.widgets['Progress Bar']
        installation_ended = central.page_object.Label(central.find_widget(widget)).get_text.splitlines()[0]
        if not expected_msg in installation_ended:
            widget = central.current_page.widgets['description']
            desc = central.page_object.Label(central.find_widget(widget)).get_text
            log.fail(f'{installation_ended} - {desc}')
            raise AssertionError(f'Not Expected Msg: {installation_ended} - {desc}')
        else:
            log.info(installation_ended)
    finally:
        widget = central.current_page.widgets['Close']
        central.page_object.Button(central.find_widget(widget)).click(pre_delay=1)
        central.set_current_page(context.last_used_page)
        handle_user_dialog(context, 'stop')


@When("I select all items in view menu")
def view_all_versions(context):
    central = context._config.central
    widget = central.current_page.widgets['Products Filter Expand']
    central.page_object.Button(central.find_widget(widget)).click()
    widget = central.current_page.widgets['Products Filter']
    central.page_object.DropDown(central.find_widget(widget)).select_all_items()
    widget = central.current_page.widgets['Products Filter Expand']
    central.page_object.Button(central.find_widget(widget)).click()


@When('I introduce reporev "{reporev}" in version "{version}"')
def change_reporev(context, reporev, version):
    context.execute_steps(u"""When I select "Settings" from Waves Central navigation menu""")
    central = context._config.central
    widget = central.current_page.reporev(version)
    if central.page_object.TextField(central.find_widget(widget)).get_text != reporev:
        central.page_object.TextField(central.find_widget(widget)).clear()
        central.page_object.TextField(central.find_widget(widget)).set_text(str(reporev))
        central.switch_to_active_element().set_text(Keys.ENTER)
        context.execute_steps(u"""When I wait for sync dialog to disappear""")


@given('I set central to run from "{server_name}"')
def set_server(context, server_name):
    """select between register and betanlb"""
    central_utils.set_server_details(server_name)

@When('I get list of all Products')
def get_all_products_list(context):
    user_data_products_dict = {}
    context.execute_steps(u"""When I select "Install Products" from Waves Central navigation menu""")
    central = context._config.central
    all_products_tab = central.current_page.widgets['All Products']
    central.page_object.Button(central.find_widget(all_products_tab)).click()
    view_all_versions(context)
    products_widgets = central.current_page.widgets['Products List']
    all_products = central.page_object.ProductsTable(central.find_widgets(products_widgets), product_widget_type=central.current_page.product_widget)
    for product_widget in all_products.products_widgets:
        central.scroll_to_element(product_widget.webelement)
        product_version = product_widget.get_major_version
        if not user_data_products_dict.get(product_version):
            user_data_products_dict[product_version] = []
        user_data_products_dict[product_version].append(product_widget.get_stripped_name())
    possible_ref_path = Path(context.report_path, 'Possible References')
    possible_ref_path.mkdir(exist_ok=True)
    server_name = context._config.central.server_name
    products_list_file = possible_ref_path.joinpath(f'all_central_products_{server_name}.yaml')   # file named after tag
    with open(products_list_file, 'w') as _f:
        yaml.dump(user_data_products_dict, _f, default_flow_style=False)
    return user_data_products_dict


@Then('Product list should be the same as the reference')
def equal_products_compare(context):
    current_products_dict = get_all_products_list(context)
    server_name = context._config.central.server_name

    reference_products_dict = {}
    reference_file = Path(context.test_reference_path).parent.parent.joinpath(f'all_central_products_{server_name}.yaml')
    if not reference_file.exists():
        log.error(f'{str(reference_file)} not exist')
    else:
        with open(reference_file, 'rb') as _f:
            reference_products_dict.update(yaml.full_load(_f))
    diff_dict = {'missing': {},
                 'extra': {}}

    for k, v in reference_products_dict.items():
        diff_dict['missing'][k] = set(v) - set(current_products_dict.get(k, set()))
        diff_dict['extra'][k] = set(current_products_dict.get(k, set())) - set(v)
        current_products_dict.pop(k, None)

    if any([f for f in diff_dict['missing'].values()] + [f for f in diff_dict['extra'].values()]):
        rep.add_label_to_step('Extra', str(diff_dict['extra']))
        rep.add_label_to_step('Missing', str(diff_dict['missing']))
        raise AssertionError(f'Product lists are different')
    if len(current_products_dict) != 0:
        rep.add_label_to_step('Extra', str(current_products_dict))
        raise AssertionError(f'Product lists are different')


@When('I run Version Organizer from Settings')
def run_version_organizer(context):
    context.execute_steps(u"""When I select "Settings" from Waves Central navigation menu""")
    central = context._config.central
    widget = central.current_page.widgets['Version Organizer Button']
    central.page_object.Button(central.find_widget(widget)).click()
    central.set_current_page(central.page_object.SettingsMaintenanceDialog('Version Organizer'))
    widget = central.current_page.widgets['Run Button']
    central.page_object.Button(central.find_widget(widget)).click()
    context.execute_steps(u'''When I wait until "OK" button appeared with message "Done"''')
    context.execute_steps(u"""When I select "Settings" from Waves Central navigation menu""")


