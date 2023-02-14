#!/usr/bin/env python

from __future__ import print_function

import datetime
import logging
import os
import shutil
import stat
import sys
import time
import zipfile
from pathlib import PurePath, Path

from infra import custom_exceptions as ce, config, logger
from utils import sub_process

log = logger.get_logger(__name__)

from functools import partial
from multiprocessing import Pool, freeze_support


def main():
    logger.set_logger(debug_to_stdout=True)
    log.info(__file__)
    return


def clear_or_create_folder(folder_path, apass=None):
    if os.path.exists(folder_path):
        remove_folder_contents(folder_path, apass=apass)
    else:
        os.makedirs(folder_path)
        log.info(f'{folder_path} was created')
    return folder_path


def split_path(file_path):
    '''A function that takes a file path and returns file dir, file name (without ext), file extension'''
    file_dir = os.path.dirname(file_path)
    file_name, file_ext = os.path.splitext(file_path)
    file_name = os.path.basename(file_name)
    return file_dir, file_name, file_ext


def resolve_system32_path(the_path):
    '''This function replaces paths that contain "System32" with "SysNative" to be able to locate system32 files on a win64 system when running python 32-Bit.
       This solves the problem of running 32-Bit Python on a 64-Bit Windows - No access to System32 folder'''
    from utils import misc_utils
    if not misc_utils.is_windows_64():
        return the_path
    else:
        if misc_utils.is_python_64():
            return the_path
        else:
            return the_path.replace('System32', 'SysNative').replace('system32', 'SysNative')


def walk_level(some_dir, level=1):
    '''This function is a generator fucntion that os.walks a certain path, but only until a certain level'''
    some_dir = some_dir.rstrip(os.path.sep)
    assert os.path.isdir(some_dir)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]


def get_relative_path(file_path, relative_folder):
    '''Returns relative path of a file compared to a folder.'''
    if not file_path.startswith(relative_folder):
        raise ce.WEIOError('File path is not related - %s, %s' % (file_path, relative_folder))
    return file_path[len(relative_folder) + 1:]


def copy_res_fork(src, dst):
    '''A function that uses the basic UNIX cp command to copy files with res fork.'''
    if sys.platform != 'darwin':
        raise ce.WEOSError('This function works only on Mac.')
    log.info('Copying %s - %s' % (src, dst))
    sub_process.sub_popen('cp', '-f', '-r', src, dst)


def mac_copy_products(src, dst, procs=1, **kwargs):
    """a main function to manage copy products for mac.
    it allows copy with multiprocessing.
    it collects src locations and pair them with their equivalents in dst"""
    log.info(f'Copying: {src} -> {dst}')
    copy_folders = sorted(Path(src).glob('*.*'))  # packages(.app, .pkg) and files(.txt) in src root folder
    copy_folders.extend(c for c in sorted(Path(src).glob('*/*/')) if c.parent not in copy_folders)  # all other folders which are not sub folder of root packages
    copy_folders = [copy_folders[i:i + procs] for i in range(0, len(copy_folders), procs)]   # split the paths in len(procs) chunks
    for folders_chunk in copy_folders:
        src_dst_tuples = [[f, Path(dst).joinpath(f.relative_to(src))] for f in folders_chunk]  # pair with relative dst path
        with Pool(len(folders_chunk)) as pool:
            pool.map(partial(ditto_pair, **kwargs), src_dst_tuples)
    if len(copy_folders) == 0:   # src is a single file as src
        copy_ditto(src, dst, **kwargs)
    log.info('Done!')


def ditto_pair(src_dst_pair, **kwargs):
    copy_ditto(*src_dst_pair, **kwargs)


def copy_ditto(src, dst, delete=False, ignore_patterns=None, run_sudo=False, copy_folder=False, **kwargs):
    """A function that uses the basic ditto command to copy directories.
     If dst folder is exist it will be overwritten, otherwise src folder will be merged with dst folder.
       Optional args:
             delete - delete src folder after copy like 'move' action
             ignore_patterns - implemented only on copy_anything
             run_sudo - run command as sudo requires apass argument
             apass - administrator password to run copy with sudo
             copy_folder - If False, content of src will be copied into dst. If True src folder will be copied
             into dst"""
    remove_dst = kwargs.pop('remove_dst', True)
    if not os.path.exists(src) and not os.path.islink(src):
        raise ce.WEFileNotFoundError('Source path does not exist: %s' % src)
    if config.current_os != 'Mac':
        raise ce.WEOSError('This function works only on Mac.')

    if os.path.isdir(src):
        if copy_folder:
            dst = os.path.join(dst, os.path.basename(src))
        if remove_dst:
            remove_paths(dst, **kwargs)
    try:
        if run_sudo and kwargs.get('apass') is not None:
            sub_process.sudo_sub_popen('ditto', src, dst, **kwargs)
        else:
            sub_process.sub_popen('ditto', src, dst, **kwargs)
        if delete:
            remove_paths(src, **kwargs)
    except Exception as e:
        log.warning(e.args[0])


def copy_if_different(src, dst):
    '''copies src to dst if file does not exist or exist with different modification date.'''
    diff_file_lst = []
    if os.path.isdir(src):
        diff_file_lst = list_diff_files(src, dst)
    elif not os.path.exists(dst) or not cmp_files_by_modification_date(src, dst):
        diff_file_lst.append({'src': src, 'dst': dst})
    if len(diff_file_lst):
        for file_dict in diff_file_lst:
            os.makedirs(os.path.dirname(file_dict['dst']), exist_ok=True)
            copy_anything(file_dict['src'], file_dict['dst'], copy_folder=False)
    else:
        log.info('No need to update file/s.')


def link_folder(src, dst):
    """A function to create symbolic links"""
    log.info(f'Creating {os.path.basename(src)} folder symlink -> {dst}')
    if config.current_os == 'Win':
        sub_process.sub_popen(f'mklink /D "{dst}" "{src}"', shell=True)
    elif config.current_os == 'Mac':
        sub_process.sub_popen('ln', '-s', src, dst)


def unlink_folder(dst):
    """A function to unlinks symbolic links"""
    log.info(f'Unlink {dst}')
    if config.current_os == 'Win':
        sub_process.sub_popen(f'rmdir "{dst}"', shell=True)
    elif config.current_os == 'Mac':
        sub_process.sub_popen(f'rm "{dst}"', shell=True)


def unlink_all_sample_libraries():
    """delete all Sample folders links in Shared or Public Users"""
    sample_library_links = Path(config.user_shared_path, 'Sample Libraries Locations')
    if not sample_library_links.exists():
        return
    remove_folder_contents(sample_library_links)


def list_diff_files(source_folder, target_folder):
    '''lists the files existing in the source folder and missing\different in target folder,
    using os.walk to recursively list files
    Args:
        source_folder - full path to the scanned source folder
        target_folder - full path to the scanned target folder'''

    diff_files_lst = []
    for root, dirs, files in os.walk(source_folder):
        for src_file_path in [os.path.join(root, file_name) for file_name in files]:
            # dst file calculation - add the src tree to the dst
            dst_file_path = os.path.join(target_folder, src_file_path.split(source_folder + os.path.sep)[1])
            if not os.path.exists(dst_file_path) or not cmp_files_by_modification_date(src_file_path, dst_file_path):
                diff_files_lst.append({'src': src_file_path, 'dst': dst_file_path})
    return diff_files_lst


def cmp_files_by_modification_date(file1_path, file2_path):
    '''compares the modification dates of the two given files. return True if equal, False if not'''
    file1_mtime = int(os.path.getmtime(file1_path))
    file2_mtime = int(os.path.getmtime(file2_path))
    return file1_mtime == file2_mtime


def copy_anything(src, dst, delete=False, no_metadata=False, log_to_debug=False, copy_folder=True, ignore_patterns=None,
                  **kwargs):
    '''A function that uses shutil to copy anything to any place (file or folder).
    NOTICE: IF COPYING FILE TO FOLDER, DST FOLDER MUST EXIST
       Arguments:
           delete - delete src folder after copy like 'move' action
           no_metadata - doesn't copy permission scheme from src. this is critical when when copying files that are read only.
           copy_folder - If False, content of src will be copied into dst. If True src folder will be copied into dst
           ignore_patterns - a pattern to be used with shutil.ignore_patterns, contain resources that will not be copied'''
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if src == dst:
        # no need to copy, return. 
        return
    if log_to_debug:
        log_lvl = logging.DEBUG
    else:
        log_lvl = logging.INFO

    if ignore_patterns is None:
        ignore_patterns = []
    if not os.path.exists(src):
        raise ce.WEFileNotFoundError('Source path does not exist: %s' % src)
    if os.path.isdir(src):
        if copy_folder:
            dst = os.path.join(dst, os.path.basename(src))
        if kwargs.get('remove_dst', True):
            remove_paths(dst)
        log.log(log_lvl, 'Copying %s - %s' % (src, dst))
        copytree(src, dst, no_metadata=no_metadata, ignore=shutil.ignore_patterns(*ignore_patterns))
        if delete:
            remove_paths(src)
    else:
        if delete:
            log.log(log_lvl, 'Moving %s - %s' % (src, dst))
            shutil.move(src, dst)
        else:
            log.log(log_lvl, 'Copying %s - %s' % (src, dst))
            if no_metadata:
                if os.path.isdir(dst):
                    dst = os.path.join(dst, os.path.basename(src))
                copy_func = shutil.copyfile
            else:
                copy_func = shutil.copy2
            try:
                copy_func(src, dst)
            except (PermissionError, IOError) as err:
                if 'Permission denied' in str(err):
                    onerror(lambda dst: copy_func(src, dst), dst, sys.exc_info())
                if 'results_mount' in str(err) and 'Operation not permitted' in str(err):
                    log.warning(str(err))
                else:
                    raise


def copy_by_extension(src, dst, ext_list):
    '''recursively copy for src all files with specified extensions using XCOPY (Windows only)'''
    src = src.replace(r'/', '\\')
    dst = dst.replace(r'/', '\\')
    if sys.platform != 'win32':
        raise ce.WEOSError('Function supported only on Windows.')
    if not os.path.exists(dst):
        try:
            os.makedirs(dst, exist_ok=True)
        except OSError as e:
            log.debug('%s. sleeping for 1 second and retrying' % e)
            time.sleep(1)
            os.makedirs(dst, exist_ok=True)
    try:
        for extension in ext_list:
            extension_files = os.path.join(src, '*' + extension)
            copy_cmd = ['xcopy', '/S', extension_files, dst]
            sub_process.sub_popen(*copy_cmd, log_stderr=False)
    except (ce.WERunTimeError, ce.WETimeOutError) as e:
        raise ce.WERunTimeError('Copy files by extension failed - %s' % e)


def copytree(src, dst, symlinks=False, ignore=None, no_metadata=False):
    """Recursively copy a directory tree using copy2().
    If no_metadata is True, the copyfile() will be used.

    If the optional symlinks flag is true, symbolic links in the
    source tree result in symbolic links in the destination tree; if
    it is false, the contents of the files pointed to by symbolic
    links are copied.

    The optional ignore argument is a callable. If given, it
    is called with the `src` parameter, which is the directory
    being visited by copytree(), and `names` which is the list of
    `src` contents, as returned by os.listdir():

        callable(src, names) -> ignored_names

    Since copytree() is called recursively, the callable will be
    called once for each directory that is copied. It returns a
    list of names relative to the `src` directory that should
    not be copied.

    XXX Consider this example code rather than the ultimate tool.

    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    os.makedirs(dst, exist_ok=True)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks, ignore, no_metadata)
            else:
                # Will raise a SpecialFileError for unsupported file types
                if no_metadata:
                    shutil.copyfile(srcname, dstname)
                else:
                    shutil.copy2(srcname, dstname)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error as err:
            errors.extend(err.args[0])
        except EnvironmentError as why:
            errors.append((srcname, dstname, str(why)))
    try:
        if not no_metadata:
            shutil.copystat(src, dst)
    except OSError as why:
        if WindowsError is not None and isinstance(why, WindowsError):
            # Copying file access times may fail on Windows
            pass
        else:
            errors.append((src, dst, str(why)))
    if errors:
        raise shutil.Error(errors)


def rename_path(old_path, new_path, **kwargs):
    '''Renames path from old name to new name. If the old file is read only, the function tries to change permissions or run sudo mv on mac'''
    if old_path == new_path: # rename file to its original name will delete the file
        return
    old_path = resolve_system32_path(old_path)
    new_path = resolve_system32_path(new_path)
    if os.path.exists(new_path):
        if kwargs.get('force'):
            os.remove(new_path)
        else:
            raise ce.WEOSError('Failed to rename folder - folder exists %s' % new_path)
    if os.path.exists(old_path):
        log.info('Renaming folder: %s <> %s' % (old_path, new_path))
        try:
            os.rename(old_path, new_path)
        except OSError:
            if sys.platform == 'darwin':
                log.info('Failed to rename due to permission issues, trying sudo "mv command"')
                sudo_rename_path(old_path, new_path, apass=kwargs.get('apass'))
            elif sys.platform == 'win32':
                os.chmod(old_path, stat.S_IWUSR)
                os.rename(old_path, new_path)
    return new_path


def move_aside(*paths, ext='_old', apass=None):
    """Rename path for future references"""
    for path in paths:
        path_old = path + ext
        if path.endswith(config.applications_exec):
            path_old = path[:-(len(config.applications_exec))] + '_old' + config.applications_exec
        if os.path.exists(path):
            remove_paths(path_old)
            rename_path(path, path_old, apass=apass)


def bring_back(*paths, ext='_old', apass=None):
    for path in paths:
        path_old = path + ext
        if path.endswith(config.applications_exec):
            path_old = path[:-(len(config.applications_exec))] + '_old' + config.applications_exec
        remove_paths(path, apass=apass)
        rename_path(path_old, path, apass=apass)


def remove_paths(*the_paths, log_to_debug=False, apass=None, timeout=0):
    """This function deletes files and folders. If the file is read only, the function runs onerror which tries to change permissions to the file.
    WARNING - On Windows symbolic links are treated as files (and not folders) and do not remove recursively the destination folder"""
    if log_to_debug:
        log_info_lvl = logging.DEBUG
    else:
        log_info_lvl = logging.INFO

    ignore_errors = sys.platform == 'darwin' and apass is not None  # ignoring errors on mac in case sudo password exists
    for the_path in the_paths:
        the_path = resolve_system32_path(the_path)
        if os.path.lexists(the_path):
            log.log(log_info_lvl, f'Removing path - {the_path}')
            try:
                if os.path.isdir(the_path) and not os.path.islink(the_path):
                    shutil.rmtree(the_path, ignore_errors=ignore_errors, onerror=onerror)
                else:
                    try:
                        os.remove(the_path)
                    except Exception as err:
                        if not ignore_errors:
                            onerror(os.remove, the_path, sys.exc_info())
                if sys.platform == 'darwin' and os.path.exists(the_path) and apass is not None:
                    log.log(log_info_lvl, 'Failed to remove due to permission issues, trying sudo "rm command"')
                    sudo_remove_path(the_path, apass=apass)
                if timeout > 0:
                    cnt = 0
                    while os.path.exists(the_path):
                        if cnt > timeout:
                            raise ce.WETimeOutError(f'Path could not be deleted after timeout ({cnt} cnt) - {the_path}')
                        cnt += 1
                        time.sleep(1)
            except Exception as err:
                if 'No such file or directory' in str(err):
                    log.log(log_info_lvl, f'Path does not exist, nothing to remove - {err}')
                else:

                    raise ce.WEOSError(
                        f'Path could not be deleted, please check permissions for file and enclosing folder - {err}')

def remove_flags(fol):
    """https://ss64.com/osx/chflags.html"""
    if config.current_os == 'Mac':
        locked_files = sub_process.sub_popen('find', fol, '-flags', 'uchg')
        if not locked_files:
            return
        for file in locked_files.split('\n'):
            if not Path(file).exists():
                log.warning('Got empty path while searching for flags')
            else:
                log.info(f'{file} have locked flag')
                sub_process.sub_popen('chflags', 'nouchg', file)

def remove_folder_contents(the_path, skip=None, delete_just='', apass=None):
    '''A function that removes all content of a folder. The function is used when the folder itself should not be removed'''
    if skip:
        paths_list = [os.path.join(the_path, item) for item in os.listdir(the_path) if
                skip not in item and delete_just in item]
    else:
        paths_list = [os.path.join(the_path, item) for item in os.listdir(the_path) if delete_just in item]
    if os.path.exists(the_path):
        remove_paths(*paths_list, apass=apass)


def remove_folder_contents_with_specific_end_name(the_path, *end_with):
    '''A function that removes all files of a folder that end with specific extension. The function is used when the folder itself should not be removed'''
    if os.path.exists(the_path):
        files = os.listdir(the_path)
        for item in files:
            if item.endswith(end_with):
                os.remove(os.path.join(the_path, item))

def remove_folder_contents_with_specific_content_in_name(the_path, content):
    '''A function that removes all files of a folder that contain specific content'''
    files = os.listdir(the_path)
    for item in files:
        if content in item:
            os.remove(os.path.join(the_path, item))


def sudo_remove_path(the_path, apass, log_to_debug=False):
    if log_to_debug:
        log_info_lvl = logging.DEBUG
    else:
        log_info_lvl = logging.INFO
    log.log(log_info_lvl, f'Removing path - {the_path}')
    sub_process.sudo_sub_popen('rm', '-f', '-v', '-R', the_path, apass=apass)


def sudo_rename_path(old_path, new_path, apass):
    sub_process.sudo_sub_popen('mv', '-f', '-v', old_path, new_path, apass=apass)


def onerror(func, path, exc_info):
    '''Error handler for ``shutil.rmtree``.
If the error is due to an access error (read only file)
it attempts to add write permission and then retries.
If the error is for another reason it re-raises the error.
Usage : ``shutil.rmtree(path, onerror=onerror)``'''
    try:
        log.debug('Changing permissions %s' % path)
        os.chmod(path, stat.S_IWUSR)
    except Exception as e:
        log.debug('Failed changing mode %s - %s' % (func.__name__, e))
        if sys.platform == 'win32':
            from utils import windows_utils
            windows_utils.grant_full_control_over_path(path)
        else:
            raise
    try:
        log.debug('Trying %s again - %s' % (func.__name__, exc_info[1]))
        func(path)
    except Exception as e:
        log.debug('Failed running %s - %s' % (func.__name__, e))
        raise


def get_sub_folders(parent_folder_path):
    '''returns a list of sub_folder names under the given parent folder'''
    sub_folders = []
    children = os.listdir(parent_folder_path)
    for child in children:
        if os.path.isdir(os.path.join(parent_folder_path, child)):
            sub_folders.append(child)
    return sub_folders


def _compress_folder_content(f_path):
    ''' Use for Mac only - compressing using tar.gz '''
    startingDir = os.getcwd()
    os.chdir(os.path.dirname(f_path))
    folder_name = os.path.basename(f_path)
    cmd = ['tar', '-zcvf', f'{folder_name}.tar.gz', folder_name]
    sub_process.sub_popen(*cmd, log_stderr=False)
    os.chdir(startingDir)
    return f'{folder_name}.tar.gz'


def _uncompress_folder_content(f_path, dst_path):
    ''' Use for Mac only - un-compressing using tar.gz '''
    startingDir = os.getcwd()
    os.chdir(os.path.dirname(f_path))
    folder_name = os.path.basename(f_path)
    cmd = ['tar', '-zxvf', folder_name, '--directory', dst_path]
    sub_process.sub_popen(*cmd, log_stderr=False)
    os.chdir(startingDir)


def zip_content(path, delete_original=False):
    if config.current_os == 'Mac':
        out_file = _compress_folder_content(path)
    else:
        dir, file_name, ext = split_path(path)
        out_file = os.path.join(dir, file_name + '.zip')
        if os.path.isfile(path):
            with zipfile.ZipFile(out_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(path)
        elif os.path.isdir(path):
            shutil.make_archive(os.path.join(dir, file_name), format='zip', root_dir=path)
    if delete_original:
        remove_paths(path)
    return out_file


def extract_zip_file(zip_file_path, dest_path, ignore_exception=False):
    '''extract zip file to a given destintaion'''
    if config.current_os == 'Mac':
        dest_path = os.path.abspath(os.path.join(dest_path, os.pardir))
        _uncompress_folder_content(zip_file_path, dest_path)
    else:
        with open(zip_file_path, 'rb') as zfh:
            z = zipfile.ZipFile(zfh)
            for file_name in z.namelist():
                try:
                    z.extract(file_name, dest_path)
                except Exception as e:
                    if not ignore_exception:
                        raise e


def find_modified_files(search_dir, start_time):
    '''Returns a list of paths in search_dir that were modified after start_time. The function is not recursive and returns only list of files'''
    return [os.path.join(search_dir, fname) for fname in os.listdir(search_dir)
            if datetime.datetime.fromtimestamp(os.stat(os.path.join(search_dir, fname)).st_mtime) > start_time]


def find_resource(folder_path, resource, search_format='*/{}*', print_exception=True):
    """Return Path object for the relevant path according to the resource  """
    try:
        return [PurePath(file_path) for file_path in Path(folder_path).glob(search_format.format(resource))]
    except (OSError, TypeError) as e:
        if print_exception:
            log.exception(e)
        return []


def find_resource_multi_location(paths_list, resource):
    '''Receives a series of paths and returns the first item it finds.'''
    for p in paths_list:
        resource_path = find_resource(p, resource, '**/{}*')
        if len(resource_path) > 0:
            return resource_path
    return []


def is_folder_empty(folder_path):
    '''A function returns true if folder is empty or does not exist, otherwise returns false'''
    return not os.path.exists(folder_path) or not bool(len(os.listdir(folder_path)))


def remove_empty_folders(folder):
    for directory, subdirs, files in os.walk(folder, topdown=False):
        if len(os.listdir(directory)) == 0:  # check whether the directory is now empty after deletions, and if so, remove it
            try:
                os.rmdir(directory)
            except OSError as e:
                log.warning('cannot delete folder: %s' % e)


def rename_file_recursively(path, old_str, new_str):
    '''A function replace old str to new string within path recursively'''
    for root, directories, files in os.walk(path):
        for item in directories + files:
            if old_str in item:
                rename_path(os.path.join(root, item), os.path.join(root, item.replace(old_str, new_str)))


def increase_max_files(apass):
    """used with func_execute() on Mac machines.
    In order to change the maximum number of open files, a plist file needs to be created
    This method will copy the plist file that is submitted to perforce, into the right place, change ownership and start the service.
    it will check for the change and report if succeeded or not"""
    if sys.platform != 'darwin':
        raise ce.WEOSError('This function works only on Mac.')
    current_max = sub_process.sub_popen('launchctl', 'limit', 'maxfiles').split()[1]
    log.info(f'number of maximium files {current_max}')
    dst_maxfiles_path = os.path.join('/Library', 'LaunchDaemons', 'limit.maxfiles.plist')
    src_maxfiles_path = os.path.join(config.utilities_folder, 'limit.maxfiles.plist')
    if not os.path.exists(src_maxfiles_path):
        raise ce.WEOSError(f'{src_maxfiles_path} does not exists')
    sub_process.sudo_sub_popen('cp', src_maxfiles_path, dst_maxfiles_path, apass=apass)
    sub_process.sudo_sub_popen('chown', 'root:wheel', dst_maxfiles_path, apass=apass)
    sub_process.sudo_sub_popen('launchctl', 'load', '-w', dst_maxfiles_path, apass=apass)
    time.sleep(3)
    new_max = sub_process.sub_popen('launchctl', 'limit', 'maxfiles').split()[1]
    if new_max == '64000':
        log.info(f'New number of maximum files open: {new_max}')
    else:
        raise ce.WENotImplementedError(f'New number of maximum open files is not 64000. {new_max}')


def append_to_file(file_path, output):
    """
    method used to append output to certain file
    Args:
        file_path: path to destination file
        output: what need to be appended
    """
    with open(file_path, 'a') as file:
        file.write(output + "\n")


def handle_net_path(net_path, dst_path=None, **kwargs):
    """mount server on mac or prepand \\ to windows"""
    if config.current_os == 'Win':
        dst = f'\\\\{net_path}'
    else:
        if dst_path is None:
            dst = os.path.join(config.default_automation_path, os.path.basename(net_path))
        else:
            dst = dst_path
    return dst


def get_latest_file(files_location, file_type='*', filename_filter=''):
    """
    This function return the latest file in a folder.
    The latest file can be conditioned by a type and/or a substring contained in it's name
    for example, to get the latest doc file that contains the string 'filename' pass to this function:
    file_type - '*docx', filename_filter - 'filename'
    """
    files = find_resource(files_location, filename_filter + file_type, '{}')
    max_file = max(files, key=os.path.getctime)
    return max_file


def path_modified_past_day(path):
    return (time.time() - os.path.getmtime(path)) < 86400


def find_waves_tools(path, tool_name, search_format='**/{}'):
    tool_paths = find_resource(path, tool_name, search_format=search_format)
    occurrences = len(tool_paths)
    if occurrences > 1:
        log.info(f'found {occurrences} of {tool_name} under {path}')
        log.info(tool_paths)
        log.info('Filter Apps/Applications content from results')
        tool_paths = [path for path in tool_paths if not any(x in ['Apps', 'Applications'] for x in path.parts)]
        occurrences = len(tool_paths)
    if occurrences == 0:
        log.info(f'{tool_name} is not find under {path}')
        return ''

    return tool_paths[0]

def copy_instrument_data_folder(setup_data, sg_setup_data=False):
    """copies instrument data folder if the folder has been modified in the past day"""
    error_msg = []
    dst_shortcut_samples_folder = os.path.join(config.user_shared_path, 'Sample Libraries Locations')
    clear_or_create_folder(dst_shortcut_samples_folder)
    setup_data_list = setup_data['sample_folders']
    if sg_setup_data:
        setup_data_list = setup_data['sg_sample_folders']
    # remove old sample library structure
    if Path(setup_data['dst_samples_location'], 'Grand Rhapsody HD').exists():
        remove_paths(setup_data['dst_samples_location'])
    for instrument in setup_data_list:
        src_samples_folder = os.path.join(setup_data['main_samples_source_path'], instrument['src'])
        dst_samples_folder = os.path.join(setup_data['dst_samples_location'], instrument['name'])
        modified_dst_samples_name = os.path.join(setup_data['dst_samples_location'], f"{instrument['name']}_old")
        try:
            if instrument['name'] == 'Waves Audio Factory Pack' and not os.path.exists(dst_samples_folder) and \
                    os.path.exists(modified_dst_samples_name):
                rename_path(modified_dst_samples_name, dst_samples_folder)
            if not os.path.exists(dst_samples_folder) or path_modified_past_day(src_samples_folder):
                log.info('Copying %s samples' % instrument['name'])
                copy_if_different(src_samples_folder, dst_samples_folder)
            if not config.current_os == 'Win' and Path(dst_samples_folder).stem != 'SD':
                dst_link_samples_folder = os.path.join(config.user_shared_path, instrument['dst'])
                link_folder(dst_samples_folder, dst_link_samples_folder)
        except Exception as e:
            msg = 'Failed to copy instrument data folder - %s' % e
            error_msg.append(msg)
            log.error(msg)
            raise e

    # copy windows sample libraries shortcuts
    if config.current_os == 'Win':
        src_shortcut_samples_folder = r'\\gimli\CRF\BDD_References\plugins_tests\sample_library_shortcuts'
        remove_paths(dst_shortcut_samples_folder)
        copy_anything(src_shortcut_samples_folder, dst_shortcut_samples_folder, copy_folder=False)

def copy_func(src, dst, **kwargs):
    func = copy_anything
    kwargs_for_copy = {}
    if config.current_os == 'Mac':
        func = copy_ditto
        kwargs_for_copy['run_sudo'] = True
    kwargs_for_copy['copy_folder'] = True
    kwargs_for_copy['timeout'] = 1200
    kwargs_for_copy.update(**kwargs)
    func(src, dst, **kwargs_for_copy)

if __name__ == '__main__':
    main()
