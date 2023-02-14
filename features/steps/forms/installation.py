import os
import glob
import random
import time
import yaml
import json
import re
from pathlib import Path
from behave import *


from infra import logger, reporter
from infra import config
from utils import files_utils, plugin_info, presets_manager
from binary_verification import verify_content, get_filepaths

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.common import exceptions


log = logger.get_logger(__name__)
rep = reporter.get_reporter()


def go_to_all_products_tab(context):
    context.execute_steps(u"""When I select "Install Products" from Waves Central navigation menu""")
    context.execute_steps(u"""When I click on "All Products" on Waves Central""")
    context.execute_steps(u"""When I select all items in view menu""")

def search_product(context, product):
    context.execute_steps(u"""When I write "%s" into "Search" text field on Waves Central""" % product)


def check_product(context, product, version):
    context.execute_steps(u"""When I check "%s" of "%s" from products list""" % (product, version))


def click_install(context):
    context.execute_steps(u"""When I click on "Install" on Waves Central""")


def choose_dont_activate(context):
    context.execute_steps(u'''When I choose "Don't Activate License" as target device''')  # from licenses.py


@When("I wait for installation to complete")
def wait_for_installation_complete(context, timeout=2700):
    central = context._config.central
    page = central.current_page
    central.set_current_page(central.page_object.ProgressDialog())
    widget = central.current_page.widgets['progress_done']
    try:
        context.execute_steps(u"""When I "start" handle user dialog""")
        central.wait_until(ec.visibility_of_element_located(widget['Locator']), timeout=timeout)
    except exceptions.TimeoutException as e:
        log.error(f'Timeout: {e}')
        context.user_data['img_path'] = central.screen_cap(os.path.join(context.report_path, 'timeout_screenshot'),
                                                           crop_to_window=False)
        widget = central.current_page.widgets['Close']
        central.wait_until(ec.element_to_be_clickable(widget['Locator']), timeout=20)
        central.page_object.Button(central.find_widget(widget)).click()
        widget = central.current_page.widgets['Yes']
        central.wait_until(ec.element_to_be_clickable(widget['Locator']), timeout=20)
        central.page_object.Button(central.find_widget(widget)).click()
        widget = central.current_page.widgets['OK']
        central.wait_until(ec.element_to_be_clickable(widget['Locator']), timeout=20)
        central.page_object.Button(central.find_widget(widget)).click()
        raise AssertionError(f'Installation Timeout')
    else:
        widget = central.current_page.widgets['Progress Bar']
        installation_ended = central.page_object.Label(central.find_widget(widget)).get_text.splitlines()[0]
        if not any(res.lower() in installation_ended.lower() for res in ['Installation completed successfully', 'install and activate complete']):
            widget = central.current_page.widgets['description']
            desc = central.page_object.Label(central.find_widget(widget)).get_text
            log.fail(f'{installation_ended} - {desc}')
            context.user_data['img_path'] = central.screen_cap(os.path.join(context.report_path, 'exception_screenshot'), crop_to_window=False)
            raise AssertionError(f'Installation Error')
        else:
            log.info(installation_ended)
        widget = central.current_page.widgets['Close']
        central.page_object.Button(central.find_widget(widget)).click(pre_delay=1)
    finally:
        central.set_current_page(page)
        context.execute_steps(u"""When I "stop" handle user dialog""")


@when('I install "{product}" version "{version}" without activation')
def install_product_without_activate(context, product, version, dependency_name='install_plugin'):
    go_to_all_products_tab(context)
    search_product(context, product)
    check_product_name(context, product, version)
    choose_dont_activate(context)
    click_install(context)
    wait_for_installation_complete(context)


@When('I install products from table of content without activation')
def install_from_list(context):
    go_to_all_products_tab(context)
    context.user_data['installed_products'] = []
    for product, version in context.table:
        search_product(context, product)
        check_product_name(context, product, version)
        context.user_data['installed_products'].append([product, version])
    choose_dont_activate(context)
    click_install(context)
    wait_for_installation_complete(context)

@when('I check "{check}" of "{version}" from licenses list')
@when('I check "{check}" of "{version}" from products list')
def check_product_name(context, check, version):
    if 'LATEST' in version:
        try:
            backward = int(version.split('-')[1])
        except IndexError:
            backward = 0
        check_latest_product(context, check, backward)
    else:
        check_product_version(context, check, version)


def check_latest_product(context, product_name, backward):
    central = context._config.central
    widgets = central.current_page.select_product(product_name, '')
    all_products_elements = central.find_widgets(widgets)
    displayed_products = central.page_object.ProductsTable(all_products_elements, product_widget_type=central.current_page.product_widget)
    try:
        latest_version = displayed_products.check_latest_backward(backward)
    except exceptions.ElementNotInteractableException:
        central.scroll_to_element(displayed_products.products_widgets[-1].webelement)
        latest_version = displayed_products.check_latest_backward(backward)
    context.user_data['central_latest'] = latest_version


def check_product_version(context, product_name, version):
    central = context._config.central
    widget = central.current_page.select_product(product_name, version)
    check_product_widget = central.current_page.product_widget(central.find_widget(widget))
    check_product_widget.check()

@then('folder "{folder_name}" should "{contain}" plugin "{plugin}" version "{version}"')
def plugins_moved_to_correct_folder(context, folder_name, contain, plugin, version):
    contain_dict = {'contain': True,
                    'not contain': False}
    folder_path = os.path.join(config.main_waves_path, folder_name)
    if not os.path.exists(folder_path):
        msg = f'''{folder_name} was not created'''
        log.info(msg)
        raise AssertionError(msg)

    found_bundle = [bundle for bundle in glob.glob(folder_path + '/*.bundle') if os.path.basename(bundle).replace('.bundle', '') in plugin]
    if contain_dict[contain] != (len(found_bundle) > 0):
        other_contain = [key for key in contain_dict.keys() if key != contain][0]
        msg = f'''folder {folder_name} {other_contain} plugin {plugin} version {version}'''
        log.info(msg)
        raise AssertionError(msg)


@When('I install "{iterations:d}" random products from all products')
def install_random_products_from_all_products(context, iterations):
    central = context._config.central
    seed = context.opt_dict.get('seed', random.randint(0, 5000))
    random.seed(int(seed))
    log.info(f'the random seed is: {seed}')
    context.execute_steps(u"""When I select "Install Products" from Waves Central navigation menu""")
    context.execute_steps(u"""When I click on "All Products" on Waves Central""")
    widget = central.current_page.widgets['Products Filter Expand']
    central.page_object.Button(central.find_widget(widget)).click()
    widget = central.current_page.widgets['Products Filter']
    items = central.page_object.DropDown(central.find_widget(widget)).get_all_items
    items[0].check()  # LATEST
    items[1].check()  # LATEST-1
    widget = central.current_page.widgets['Products Filter Expand']
    central.page_object.Button(central.find_widget(widget)).click()

    products_list_widget = central.current_page.widgets['Products List']
    all_products = central.find_widgets(products_list_widget)

    i = 0
    while i != iterations:
        random_number = random.choice(range(len(all_products)))
        log.debug(f'product random number: {random_number}')
        random_selection = all_products[random_number]
        central.scroll_to_element(random_selection)
        product_widget = central.page_object.Table([random_selection], products_list_widget['table'])[0]
        product_name = product_widget['product_name'].get_text
        if product_name == '':
            continue
        version = product_widget['product_version'].get_text.split('.')[0][-2:]  # good for both 'V13.0.0' and 'V 13.0.0'
        i += 1
        check_product_name(context, product_name, version)
    # choose_dont_activate(context)
    click_install(context)
    start_time = time.time()
    wait_for_installation_complete(context)
    total_time = time.time() - start_time
    add_install_timing_info(total_time, context, 'random products', '', 'install')

def add_install_timing_info(total_time, context, product_name, version, mode):
    import glob
    import re
    timings_files = glob.glob(os.path.join(config.waves_central_default_log_folder, 'install', '*.log'))
    recent_file = max(timings_files, key=os.path.getmtime)
    stages_to_report = []
    with open(recent_file, 'r') as f:
        for num, line in enumerate(f, 1):
            if ('Run time:' in line):
                total_time_from_log = line.split('|')[2].strip()[10:-4]
                total_time_in_sec = int(total_time_from_log.split('.')[0])
                import datetime
                total_time_from_log = str(datetime.timedelta(seconds=total_time_in_sec))
                break
    columns = [('stage', 'Info'), ('duration', 'Duration')]

    timings_files = glob.glob(os.path.join(config.waves_central_default_log_folder, 'install', '*.timings.py'))
    recent_file = max(timings_files, key=os.path.getmtime)
    stages_to_report = []
    with open(recent_file, 'r') as f:
        for num, line in enumerate(f, 1):
            if ('with Stage' in line or 'with PythonBatchRuntime' in line) and (
                    line.startswith('w') or line.startswith('    w')):
                stages_to_report.append(line.strip())
            elif 'MAX_REPO_REV' in line:
                context.used_repo[f'V{version}'] = line.split('=')[1].strip()

    if not context._config.timing_summary_step.get(product_name, False):
        context._config.timing_summary_step[product_name] = []
        context._config.phase_number[product_name] = 1

    table_name = f'Durations #{context._config.phase_number[product_name]} - {product_name} {version}'
    timing_info = {}
    rep.add_table(table_name, caption=table_name, type='iterable')
    rep.add_columns(table_name, *columns)
    rep.add_row(table_name, ['Actual Total installation time from GUI',
                             time.strftime('%H:%M:%S', time.gmtime(total_time.__round__(2)))])
    rep.add_row(table_name, ['Total time from Log', total_time_from_log])

    for stage in stages_to_report:
        stage_text, duration = stage.split('#')
        stage_name = re.findall('"([^"]*)"', stage_text)[0]
        if stage_name == 'epilog':
            continue
        timing_m, timing_s = duration.split(':')
        timing_m = int(timing_m[:-1])
        timing_s = float(timing_s[:-1])
        timing_h = int(timing_m / 60)
        timing_m = int(timing_m - (timing_h * 60))
        duration = f'{timing_h}:{timing_m:02d}:{timing_s:02.02f}'
        rep.add_row(table_name, [stage_name, duration])
        timing_info[stage_name] = duration
    timing_info['total'] = total_time_from_log
    context._config.timing_summary_step[product_name].append(timing_info)
    rep.add_table_to_step(table_name)
    context._config.phase_number[product_name] = context._config.phase_number[product_name] + 1

    file_name = f"{product_name}_{version}_{mode}_timing_history.csv"
    file_name = re.sub(r'[\\/*?!#:"<>|@]', '_', file_name)  # remove illegal characters from file name
    central = context._config.central
    timing_history = os.path.join(context.reference_path, 'Central_Testing', 'Content',
                                  central.server_settings['server_name'], config.current_os,
                                  file_name)

    from datetime import datetime
    now = datetime.now()
    # dd/mm/YY H:M:S
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    job_id = context.opt_dict.get('job_id', context.step_id)
    fields = [dt_string, job_id, total_time_from_log]

    if context._config.timing_histories_file.get(timing_history, False):
        context._config.timing_histories_file[timing_history].append(total_time_from_log)
    else:
        context._config.timing_histories_file[timing_history] = [dt_string, job_id, context.used_repo[f'V{version}'],
                                                                 context.url, total_time_from_log]

    import csv
    if not os.path.exists(timing_history):
        os.makedirs(Path(timing_history).parent, exist_ok=True)
        file_header = ['Date', 'Job_Id', 'Repo_Rev', 'Report_Link', 'Durations']
        with open(timing_history, 'w+') as f:
            writer = csv.writer(f)
            writer.writerow(file_header)


def install(context, product_name, version, verify_content=True):
    go_to_all_products_tab(context)
    search_product(context, product_name)
    check_product_name(context, product_name, version)
    click_install(context)
    start_time = time.time()

    try:
        central = context._config.central
        central.set_current_page(central.page_object.UnSupportedOS())
        widget = central.current_page.widgets['Continue']
        central.page_object.Button(central.find_widget(widget)).click()
    except Exception as e:
        pass

    wait_for_installation_complete(context)
    total_time = time.time() - start_time
    mode = 'install'
    add_install_timing_info(total_time, context, product_name, version, mode)
    if verify_content:
        if not validate_all_contents(context, mode, product_name, version):
            raise AssertionError('Content validation failure')


@Then(
    'I compare current machine content status to reference of install from "{mode}" of products "{product_name}" from version "{version}"')
def validate_all_contents(context, mode, product_name, version):
    if 'latest' in version.lower():
        try:
            backward = int(version.split('-')[1])
        except IndexError:
            backward = 0
        version = str(context.user_data['central_latest'] - backward)
    installed_binaries = {'WaveShell': [], 'support_dir_path': [], 'user_shared_path': [], 'nks_dir_path': [],
                               'main_waves_path': []}
    extensions = ('.bundle', '.aaxplugin', '.dll', '.vst3', '.vst', '.app', '.dylib', '.component', '.framework', '.wfi')

    for shell, path_to_shell in config.system_shells_paths.items():
        installed_binaries['WaveShell'].extend(get_filepaths(path_to_shell, search_for=['WaveShell'],
                                                                  extension=extensions, add_postfix=False))

    installed_binaries['support_dir_path'].extend(get_filepaths(config.support_dir_path, skip=['Redis', 'Licenses'],
                                                                     extension=['.bundle', '.dll', '.py', '.yaml', '.txt'],
                                                                     add_postfix=False))

    installed_binaries['user_shared_path'].extend(get_filepaths(config.user_shared_path, add_postfix=False))

    installed_binaries['nks_dir_path'].extend(get_filepaths(config.nks_dir_path, search_for=['Waves-'], add_postfix=False))

    for fol in os.listdir(config.main_waves_path):
        path = os.path.join(config.main_waves_path, fol)
        if 'Plug' in fol:
            installed_binaries['main_waves_path'].extend(get_filepaths(path, extension=['.bundle', '.pdf', '.dll'],
                                                                            add_postfix=False))
        elif 'WaveShell' in fol:
            installed_binaries['main_waves_path'].extend(get_filepaths(path, search_for=['WaveShell'], extension=extensions,
                                                                            add_postfix=False))
        else:
            installed_binaries['main_waves_path'].extend(get_filepaths(path, add_postfix=False))

    if config.current_os == 'Mac':
        installed_binaries['waves_plist_for_ni'] = []
        installed_binaries['waves_plist_for_ni'].extend(
            get_filepaths(config.waves_plist_for_ni, search_for=['com.native-instruments.Waves-'], add_postfix=False))

    for j in installed_binaries.keys():
        installed_binaries[j] = [add_version_to_path(context, a) for a in installed_binaries[j]]
    file_name = f"{product_name}_*_{mode}.json"

    central = context._config.central
    all_files_ref_file = sorted(Path(context.reference_path, 'Central_Testing', 'Content',
                                      central.server_settings['server_name'], config.current_os).glob(file_name))
    try:
        backward = int(version.split('-')[1])
    except IndexError:
        backward = 0
    version_index = (-1-backward)
    try:
        exp_files_ref_file = all_files_ref_file[version_index]
    except IndexError:
        log.error(f'{version} is missing, verification step will be skipped but result file remain')
        exp_files_list = {'WaveShell': [], 'support_dir_path': [], 'user_shared_path': [], 'nks_dir_path': [],
                          'main_waves_path': []}
        if config.current_os == 'Mac':
            exp_files_list['waves_plist_for_ni'] = []
        rep.add_label_to_step('No Reference',
                              f'No Reference for the current plugin found in {version}')
    else:
        rep.add_txt_file_content_to_step(exp_files_ref_file, 'Reference of Installed File')
        with open(exp_files_ref_file, 'r') as stream:
            exp_files_list = json.load(stream)

    missing = []
    extra = []
    for key in installed_binaries.keys():
        actual = set(installed_binaries[key])
        expected = set(exp_files_list[key])
        missing.extend(expected - actual)
        extra.extend(actual - expected)

    need_reference = False
    return_status = True
    if len(missing) > 0:
        need_reference = True
        return_status = False
        report_files_list(sorted(missing), 'Missing', report_as_failures=True)
    if len(extra) > 0:
        need_reference = True
        report_files_list(sorted(extra), 'Extra', report_as_failures=False)
    if need_reference:
        file_name = f"{product_name}_{version}_{mode}.json"
        rep.add_label_to_step('New Reference',
                              f'New Reference for the current plugin found in /Report Folder/possible_reference/')
        act_files_res_file = os.path.join(context.report_path, 'possible_reference', file_name)
        os.makedirs(os.path.join(context.report_path, 'possible_reference'), exist_ok=True)
        with open(act_files_res_file, 'w') as stream:
            json.dump(installed_binaries, stream, indent=4)

    return return_status

def add_version_to_path(context, filepath):
    extensions = ('.bundle', '.aaxplugin', '.dll', '.vst3', '.vst', '.app',
                  '.dylib', '.component', '.framework', '.wfi', '.xml')
    if Path(filepath).suffix not in extensions:
        return filepath
    app = context._config.central
    log.debug(f'Adding version to {filepath}')
    if filepath.endswith('bundle'):
        return f"{filepath}_{app.get_plugin_version(filepath)}"
    if Path(filepath).name == 'Info.xml':
        return f"{filepath}_{app.get_version_from_info_xml(filepath)}"
    if 'Waveslib' in filepath:
        return f"{filepath}_{app.get_waveslib_version(filepath)}"
    if 'WaveShell' in filepath:
        return f"{filepath}_{app.get_waveshell_version(filepath, version_type='long')}"
    return app.get_version_from_dll(filepath)


@when('I install "{product_name}" version "{version}" and verify content')
def install_activate_and_verify(context, product_name, version):
    context._config.last_installed_plugin = product_name
    context._config.last_installed_plugin_version = version
    install(context, product_name, version, verify_content=True)


@when('I install "{product_name}" version "{version}"')
def install_and_activate(context, product_name, version):
    install(context, product_name, version, verify_content=False)


@When('I install and activate products from table of content')
def install_and_activate_from_list(context):
    go_to_all_products_tab(context)
    context.user_data['installed_products'] = []
    for product, version in context.table:
        search_product(context, product)
        check_product(context, product, version)
        context.user_data['installed_products'].append([product, version])
    click_install(context)
    wait_for_installation_complete(context)


@When('I install the suggested updates')
def install_updates(context):
    central = context._config.central
    widget = central.current_page.widgets['update products list OK Button']
    central.page_object.Button(central.find_widget(widget)).click()
    widget = central.current_page.widgets['update Button']
    central.page_object.Button(central.find_widget(widget)).click()
    wait_for_installation_complete(context)


@Then('I verify "{product_name}" version "{version}" was installed properly')
def verify_content(context, product_name, version):
    if not validate_all_contents(context, 'install', product_name, version):
        raise AssertionError('Content validation failure')


@Then('I verify all installed_products was installed properly')
def verify_all_installed_content(context):
    for product_name, version in context.user_data['installed_products']:
        verify_content(context, product_name, version)


def report_files_list(items_list, table_name, report_as_failures=True):
    rep.add_table('Content verification ' + table_name, caption='Content verification - ' + table_name, type='iterable')
    rep.add_columns('Content verification ' + table_name, ('path', 'Path'))
    row_tags = {}
    if report_as_failures:
        row_tags = {'bgcolor': 'pink', 'type': 'fail'}
    for item in items_list:
        rep.add_row('Content verification ' + table_name, [item], **row_tags)
    rep.add_table_to_step('Content verification ' + table_name)


def validate_content_from_list(actual_installed_shells, context, mode, name, product_name, version):
    file_name = f"{product_name}_{version}_{mode}_{name}.json"
    exp_files_ref_file = os.path.join(context.reference_path, 'Central_Testing', 'Content',
                                      context._config.central.server_settings['server_name'], config.current_os,
                                      file_name)
    has_reference = True
    if not os.path.exists(exp_files_ref_file):
        log.error(f'{exp_files_ref_file} is missing, verification step will be skipped but result file remain')
        exp_files_list = {'product_list': []}
        has_reference = False
    else:
        with open(exp_files_ref_file, 'r') as stream:
            exp_files_list = json.load(stream)
    columns = [('expected', 'Expected Files Count'), ('actual', 'Actual Files Count')]
    rep.add_table(f'binaries count on {name}',
                  caption=f'Products folder verification over {name}')
    rep.add_columns(f'binaries count on {name}', *columns)
    rep.add_row(f'binaries count on {name}'
                , [len(exp_files_list['product_list']) if has_reference else 'No Reference for this validation',
                   len(actual_installed_shells['product_list'])])
    rep.add_table_to_step(f'binaries count on {name}')
    actual_installed_shells_set = set(actual_installed_shells['product_list'])
    exp_files_list_set = set(exp_files_list['product_list'])
    if actual_installed_shells_set != exp_files_list_set:
        act_files_res_file = os.path.join(context.report_path, 'possible_reference', file_name)
        os.makedirs(os.path.join(context.report_path, 'possible_reference'), exist_ok=True)
        with open(act_files_res_file, 'w') as stream:
            json.dump(actual_installed_shells, stream, indent=4)
        if len(exp_files_list_set - actual_installed_shells_set) > 0:
            report_delta(sorted(exp_files_list_set - actual_installed_shells_set), f'Missing from {name}')
            rep.add_table_to_step(f'Content verification Missing from {name}')
            return False
        if len(actual_installed_shells_set - exp_files_list_set) > 0:
            report_delta(sorted(actual_installed_shells_set - exp_files_list_set), f'Extra on {name}',
                         ignore_extras=False)
            rep.add_table_to_step(f'Content verification Extra on {name}')
    else:
        log.info('Verification succeeded')
    return True


def report_delta(items_list, item_type, ignore_extras=False, description_name=None):
    """ Report differences between actual and expected
    ignore_extras - flagging to only info log the extra files"""
    if description_name == None:
        description_name = item_type
    artist_names = {}
    if items_list:
        dir_flag = ''
        err_flag = ''

        rep.add_table('Content verification ' + item_type, caption='Content verification - ' + description_name)
        rep.add_columns('Content verification ' + item_type, ('status', 'Status'), ('path', 'Path'))

        for path in sorted(items_list):
            if dir_flag == '' or dir_flag not in path:
                if path[-4:] == ' (D)':
                    dir_flag = path[:-4]
                    err_flag = item_type + ' (folder)'
                elif path[-4:] == ' (F)':
                    err_flag = item_type

            if err_flag != '':
                if not ignore_extras:
                    row_tags = {'bgcolor': 'pink', 'type': 'fail'}
                else:
                    row_tags = {'bgcolor': 'lavender', 'type': 'info'}
                if 'ArtistDLLs' in item_type and '.bundle' in dir_flag:
                    artist_num = re.sub("[^0-9]", '', dir_flag)
                    artist_names[artist_num] = artist_names.get(artist_num,
                                                                plugin_info.get_artistdll_plugin(artist_num))
                    path = f"{artist_names[artist_num]} {path}"
                rep.add_row('Content verification ' + item_type, [err_flag, path[:-4]], **row_tags)
                err_flag = ''


@when('I uninstall all products')
def uninstall_all_products(context):
    products = ['all']
    uninstall(context, *products)

@When('I uninstall "{product}"')
def uninstall_product(context, product):
    products = [product]
    uninstall(context, *products)

@when('I uninstall products from table of content')
def uninstall_selected_products(context):
    products = []
    for p in context.table:
        products.append(p['products'])
    uninstall(context, *products)

def uninstall(context, *products):
    log_docker_icons(context)
    if os.path.exists(os.path.join(config.support_dir_path, 'Waves Local Server')):
        files_utils.remove_folder_contents(os.path.join(config.support_dir_path, 'Waves Local Server'))
    context.execute_steps(u"""When I select "Settings" from Waves Central navigation menu""")
    log.info('Uninstall...')

    central = context._config.central
    widget = central.current_page.widgets['Uninstall Dropdown']
    central.page_object.Button(central.find_widget(widget)).click()
    widget = central.current_page.widgets['Uninstall Checkboxes']
    uninstall_items = central.page_object.Table(central.find_widgets(widget), widget['table'])
    for item in uninstall_items:
        if any(p for p in [item['label'].get_text, 'all'] if p in products):
            item['checkbox'].check()
    widget = central.current_page.widgets['Uninstall Button']
    central.page_object.Button(central.find_widget(widget)).click()
    central.set_current_page(central.page_object.ProgressDialog())
    widget = central.current_page.widgets['OK']
    try:
        context.execute_steps(u"""When I "start" handle user dialog""")
        central.wait_until(ec.element_to_be_clickable(widget['Locator']), timeout=1800)
    except exceptions.TimeoutException as e:
        log.error(f'Timeout {e}')
        central.switch_to_active_element().set_text(Keys.ENTER)
        raise
    else:
        widget = central.current_page.widgets['Progress Bar']
        uninstall_ended = central.page_object.Label(central.find_widget(widget)).get_text.splitlines()[0]
        if not 'Successfully uninstalled' in uninstall_ended:
            log.fail(f'Uninstall Failed {uninstall_ended}')
            raise AssertionError(f'Uninstall Failed {uninstall_ended}')
        else:
            log.info(uninstall_ended)
        widget = central.current_page.widgets['OK']
        central.page_object.Button(central.find_widget(widget)).click(pre_delay=1)
    finally:
        context.execute_steps(u"""When I "stop" handle user dialog""")
        log_docker_icons(context)
    mode = 'Uninstall'
    if hasattr(context._config, 'last_installed_plugin'):
        product_name = context._config.last_installed_plugin
        version = context._config.last_installed_plugin_version
        if not validate_all_contents(context, mode, product_name, version):
            raise AssertionError('Content validation failure')
    else:
        log.info('Content validation skipped, no info about last installed plugin')

def log_docker_icons(context):
    if config.current_os  == 'Mac':
        from utils.mac_utils import get_dock_icons
        context.user_data['docker_icons'] = get_dock_icons()
        log.debug(f"Apps in Dock: {context.user_data['docker_icons']}")


@When('I install SG Application "{app_name}"')
def install_sg_app(context, app_name):
    go_to_all_products_tab(context)
    search_product(context, app_name)
    check_latest_product(context, app_name)
    choose_dont_activate(context)
    click_install(context)
    wait_for_installation_complete(context)


@When('I "{mode}" the "{samples_type}" sample library of "{instrument_name}" version "{version}"')
def select_sample_library(context, mode, samples_type, instrument_name, version):
    central = context._config.central
    go_to_all_products_tab(context)
    search_product(context, instrument_name)
    widget = central.current_page.select_product(instrument_name, version)
    instrument_widget = central.current_page.product_widget(central.find_widget(widget))
    instrument_widget.check()
    mode = mode.lower()
    instrument_widget.select_sample_pack(mode, samples_type)

@When('I change sample libraries data folder location to "{data_folder_path}"')
def change_sample_library_location(context, data_folder_path):
    central = context._config.central
    Path(config.desktop, 'Automation', data_folder_path).mkdir(exist_ok=True)
    context.execute_steps(u"""When I select "Settings" from Waves Central navigation menu""")
    widget = central.current_page.widgets['sample library data folder button']
    central.find_widget(widget).click()
    context.execute_steps(u"""When I choose path "{}" from system dialog""".format(data_folder_path))


@Then('the "{samples_type}" samples for "{instrument_name}" version "{version}" should be automatically selected for installation')
def verify_selected_sample_library(context, samples_type, instrument_name, version):
    central = context._config.central
    go_to_all_products_tab(context)
    search_product(context, instrument_name)
    widget = central.current_page.select_product(instrument_name, version)
    instrument_widget = central.current_page.product_widget(central.find_widget(widget))
    instrument_widget.check()
    time.sleep(5)
    checked_samples = instrument_widget.is_any_sample_pack_selected
    if samples_type == 'NO' and bool(checked_samples):
        raise AssertionError(f'{instrument_widget.is_any_sample_pack_selected} Samples are checked for {instrument_name} V{version}')
    if samples_type != 'NO' and not instrument_widget.is_sample_pack_selected(samples_type):
        raise AssertionError(f'{samples_type} Samples are not checked for {instrument_name} V{version}')


@then('Central runs as "{process_type}" process')
def verify_process_type(context, process_type):
    if not config.current_os == 'Mac':
        raise EnvironmentError('This step is only for Mac')
    central = context._config.central
    current_process_type = central.get_process_kind()
    current_process_name = {'x86_64': 'Intel' ,
                            'arm64': 'ARM'}[current_process_type]
    if current_process_name != process_type:
        raise AssertionError('Process types are different')


@given('I use Central plugins from "{version}"')
def set_environment_after_central(context, version: str):
    try:
        backward = int(version.split('-')[1])
    except IndexError:
        backward = 0
    version_index = (-1-backward)
    all_plugins_folders = sorted(Path(config.main_waves_path).glob('Plug-Ins*'))
    plugins_path = str(all_plugins_folders[version_index])
    if hasattr(context, 'info_to_check_deploy'):
        version = context.info_to_check_deploy['requested_job_version_to_deploy']
        plugins_path = os.path.join(config.main_waves_path, f'Plug-Ins V{version}')

    context.user_data['plugins_info'] = plugin_info.find_xml_info([plugins_path], thng_types=('raPI', 'nsPI'), affs=('DAE_',), find_children=False, parse_gui_xml=True, force_find_presets=True, use_dbsql=False)
    context.user_data['waves_path'] = config.main_waves_path
    context.user_data['plugins_path'] = plugins_path
    context.user_data['shells_path'] = plugins_path.replace('Plug-Ins', 'WaveShells')
    context.data_folder = Path(config.main_waves_path).joinpath('Data')
    presets_paths = [context.data_folder / 'Presets']
    presets_manager.find_plugins_presets(context.user_data['plugins_info'], presets_paths)


@When('I restart the machine and continue from the next scenario')
def restart_and_continue_from_next_scenario(context):
    with open(config.start_from_scenario_file, 'w+') as res:
        res.write(yaml.safe_dump({context.feature_file_name: context._runner.config.current_scenario_index + 1}))

    if context.is_nightly:
        select_query = f'SELECT auto_params FROM automation_t WHERE rid ={context.rid}'
        test_row = context.sql_build_machine_db_obj.execute_query(select_query)
        auto_params = test_row[0].get('auto_params', '')
        dedicated_client = f"dedicated_client={config.client_name}"
        if len(auto_params) > 0 and 'dedicated_client' not in auto_params:
            auto_params += f','
        if 'dedicated_client' not in auto_params:
            auto_params += dedicated_client
        context.sql_build_machine_db_obj.update_table('automation_t',
                                           columns_to_update={'status_info': 'Restart Requested. to be continue',
                                                              'auto_params': auto_params},
                                           where_filter={'rid': f'={context.rid}'})
    context._config.restart_machine = True

@When('I install instruments with specific samples')
def install_instrument_with_specific_samples(context):
    """
        use this step for installing multiple sample based instruments.
        it's mandatory to pass a table of content to this step, table format:
            |product |version   |samples|
        if multiple sample types are required, it should be seperated by a comma
        for example:
            |product|version|samples|
            |Inspire|14     |SD,HD  |
            |COSMOS |14     |SAMPLES|
        """
    go_to_all_products_tab(context)
    context.user_data['installed_products'] = context.user_data.get('installed_products', [])
    products_name = '|'
    products_version = ''
    for product, version, samples in context.table:
        search_product(context, product)
        check_product_name(context, product, version)
        for sample in samples.upper().split(','):
            select_sample_library(context, 'select', sample, product, version)
        context.user_data['installed_products'].append([product, version])
        products_name += (product + '|')
        if products_version == version or products_version == '':
            products_version = version
        else:
            products_version = 'Multiple Versions'
    click_install(context)
    start_time = time.time()
    wait_for_installation_complete(context, timeout=4000)
    total_time = time.time() - start_time
    mode = 'install'
    add_install_timing_info(total_time, context, products_name, products_version, mode)

