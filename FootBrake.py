import PySimpleGUI as sg
import os
import shutil
import datetime
import time
import yaml
from python_get_resolve import GetResolve


def mp_add_source(fpath, add_files_flag, media_pool, media_storage):
    """
        add source clips to Resolve.
    :param fpath: footage folder path in OS.
    :param add_files_flag: if True,add folders and files, if Fasle, add folder structure only.
    :param media_pool: media pool object from Resolve API.
    :param media_storage: media storage object from Resolve API.
    :return: none
    """
    folder_handles = []
    i = 1
    for root, dirs, files in os.walk(fpath):
        # walk the folders
        if dirs:
            sub_temp = []
            cf = media_pool.GetCurrentFolder()
            # remember handle of current mediapool root
            for dir in dirs:
                sub_temp.append(media_pool.AddSubFolder(cf, dir))
            media_pool.SetCurrentFolder(cf)
            # AddSubFolder changes currentfolder to new added, return to cf
            if add_files_flag:
                for file in files:
                    media_storage.AddItemsToMediaPool(os.path.join(root, file))
            media_pool.SetCurrentFolder(sub_temp[0])
            # change current folder to the next root folder os.walk() returns, which is sub_temp[0]
            folder_handles.extend(sub_temp)
            # store sub folders handles to the list
        if not dirs:
            # if subfolder does not exist, move on to the next folder in the folder_handles list

            # add the files  first
            if add_files_flag:
                for file in files:
                    media_storage.AddItemsToMediaPool(os.path.join(root, file))

            # if next folder exist, change to next folder
            try:
                if folder_handles[i]:
                    media_pool.SetCurrentFolder(folder_handles[i])
                    i += 1
            except IndexError:
                pass


def get_all_subfolders(mp_folder):
    """
    Returns a list of all sub folders/bins objects inside the provided folder object.
    :param mp_folder: Resolve media pool folder object
    :return: a list of all the sub folders' folder object.
    """
    folderlist = []
    folderlist += mp_folder.GetSubFolders().values()
    for sub_folder in mp_folder.GetSubFolders().values():
        folderlist += get_all_subfolders(sub_folder)
    return folderlist


def make_timeline_with_folder(mp_folder, notes, timeline_notes_flag, media_pool):
    """
      Makes a timeline with all clips in a Resolve media pool bin;
    :param mp_folder: media pool bin object from Resolve's API.
    :param notes: note string for makers.
    :param timeline_notes_flag: if True,  each bin/sub-bin will be marked on the timeline.
    :param media_pool: medida pool object from Resolve's API.
    :return: Resolve object of the newly created timeline.
    """
    mp_folder_name = mp_folder.GetName()

    # initialize timeline and marker
    media_pool.SetCurrentFolder(media_pool.GetRootFolder())
    new_timeline = media_pool.CreateEmptyTimeline(mp_folder_name)
    media_pool.SetCurrentFolder(mp_folder)
    media_pool.AppendToTimeline(list(mp_folder.GetClips().values()))

    if timeline_notes_flag:
        new_timeline.AddMarker(new_timeline.GetEndFrame() - new_timeline.GetStartFrame(),
                               'Green', mp_folder_name, notes, 1)

    '''Below adds clips inside bin to timeline, and adds marker at the last clip of each bin if required.
    (because note function is written for another tool, don't see too much use here, thus the note parameter is
    not exposed to the GUI)'''

    bin_list = get_all_subfolders(mp_folder)
    for bin in bin_list:
        clips_in_this_subfolder = []
        for clip in bin.GetClips().values():
            clips_in_this_subfolder.append(clip)
            # Get all clip objects
        media_pool.AppendToTimeline(clips_in_this_subfolder)
        if timeline_notes_flag:
            new_timeline.AddMarker(new_timeline.GetEndFrame() - new_timeline.GetStartFrame(),
                                   'Green', bin.GetName(), notes, 1)
    return new_timeline


def yaml_load(filepath):
    """
    Load data from yaml file.
    :param filepath: the yaml file path.
    :return: yaml data, if failed to load will return empty dictionary.
    """
    try:
        with open(filepath, 'r') as filehandle:
            try:
                data = yaml.load(filehandle, Loader=yaml.SafeLoader)
            except:
                data = {}
    except:
        data = {}
    return data


def yaml_dump(data, filepath):
    with open(filepath, 'w') as filehandle:
        try:
            yaml.dump(data, filehandle)
        except:
            pass


def yaml_config_write():
    """
    Writes config file.
    :return: none
    """
    yaml_dump(config, os.path.join(config_path, 'config.yaml'))


def get_render_presets():
    """
    Get render presets from Resolve's API.
    On my mac, custom render presets is from No.19 and on, if it differs on your system, you may see some presets missing.
    Just need to figure out your magic number by running:
    print(proj.GetRenderPresets())
    And replace the 19 with it.
    :return: none
    """
    global preset_list
    if custom_preset_flag:
        preset_list = list(proj.GetRenderPresets().values())[19:len(proj.GetRenderPresets())]
    else:
        preset_list = list(proj.GetRenderPresets().values())[0:len(proj.GetRenderPresets())]


def refresh_presets():
    """
    Update the presets list in the GUI.
    :return: none
    """
    global preset_list
    global latest_preset
    get_render_presets()
    window['RENDERPRESET'](preset_list)
    # restore previously selected preset after refresh
    if latest_preset in preset_list:
        window['RENDERPRESET'].SetValue(latest_preset)
    else:
        window['RENDERPRESET'].SetValue([])
        latest_preset = []


def refresh_folders(watch_path):
    """
    Update the source folder list in the GUI.
    :param watch_path: the latest watch folder path.
    :return: none
    """
    path_list = []
    for item in os.listdir(watch_path):
        if os.path.isdir(os.path.join(watch_path, item)):
            path_list.append(item)
    window['SOURCEPATHS'](path_list)


def import_timeline(watch_path, folder_name):
    """
    Import footage and make timeline.
    :param watch_path: the path of watch folder.
    :param folder_name: source folder name.
    :return: True if media is imported and timeline is created successfully, False if failed.
    """
    # Add empty folder(bin) in Resolve media pool
    imported_mp_folder = mp.AddSubFolder(mp.GetRootFolder(), f"{datetime.datetime.now():%Y%m%d_%H%M%S_}" + folder_name)
    if imported_mp_folder:
        mp_add_source(os.path.join(watch_path, folder_name), 1, mp, ms)
        make_timeline_with_folder(imported_mp_folder, '', 0, mp)
        return True
    else:
        # If failed to create a new bin in media pool
        return False


def update_render_status():
    """
        Get job status by index, updates the render status table in the GUI
    :return: none
    """
    status_table = []
    for k in sorted(set(finished_queue + pending_queue)):
        try:
            status = proj.GetRenderJobStatus(k)
            status.update({'Idx': k, 'Name': proj.GetRenderJobs()[k]['TimelineName']})
            # The status_table is a list of lists, the order corresponds to the 'headings' list
            status_table.append([
                str(status.get('Idx', 'Unknown')), status.get('Name'),
                status.get('JobStatus'), int(status.get('CompletionPercentage', 'NA')),
                str(datetime.timedelta(milliseconds=status.get('TimeTakenToRenderInMs', 0))).split('.', 2)[0]
            ])
        except:
            pass
    window['TABLE'](status_table)
    window.refresh()


def queue_render(presetname, queue_source_folder):
    """
    Add a render job to the queue.
    :param presetname: the render preset to use for this job
    :param queue_source_folder: the source folder name for this job, will be added to queue_path, for the xml copy function
    :return: none
    """
    global pending_queue
    global queue_paths
    proj.LoadRenderPreset(presetname)
    if int(valid_video_track_count(proj.GetCurrentTimeline())) != 0:
        set_output_path()
        proj.AddRenderJob()
        new_job_idx = get_newest_renderjob_index()
        if new_job_idx:
            pending_queue.append(new_job_idx)
            # There is already a render_status table for showing job info on the GUI.
            # This queue_path dictionary is added later, to correspond each job index to its source and output paths.
            # Maybe can use a better data structure to manage both?
            queue_paths.update({new_job_idx: [latest_watch_path, queue_source_folder, latest_output_path]})
            update_render_status()
        else:
            sg.Popup('Failed to add render job, check Resolve.')
    else:
        sg.Popup('Failed to add render job, empty folder?')


def get_newest_renderjob_index():
    """
    Get the index of the newest job in Resolve's render queue.
    :return: the index number in integer, None if failed to get any job info.
    """
    if proj.GetRenderJobs():
        newest_index = int(max(k for k, v in proj.GetRenderJobs().items()))
        return newest_index
    else:
        return None


def valid_video_track_count(timeline):
    """
    Count non-empty video tracks in current Resolve timeline.
    :param timeline: Resolve timeline object.
    :return: integer
    """
    i = 0
    for track in range(1, int(timeline.GetTrackCount('video')) + 1):
        if timeline.GetItemsInTrack('video', track):
            i += 1
    return i


def update_table_while_rendering():
    """
    Continuously get render status of all the jobs, finished and ongoing, from Resolve, and update the GUI.
    :return: none
    """
    while proj.IsRenderingInProgress():
        update_render_status()
        # update info every 0.5 second
        time.sleep(0.5)
        if copy_xml_flag:
            for k in pending_queue:
                if k not in xml_copied:
                    # copy xml as soon as job status is 'complete', so don't have to wait for other jobs to finish
                    if proj.GetRenderJobStatus(k)['JobStatus'] == 'Complete':
                        copy_xml(queue_paths[k][0], queue_paths[k][1], queue_paths[k][2])
                        xml_copied.append(k)
    update_render_status()


def set_output_path():
    """
    Get the latest output path from the GUI and submit to Resolve.
    :return: none
    """
    global latest_output_path
    latest_output_path = values['OUTPUTPATH']
    if proj.IsRenderingInProgress():
        sg.Popup('Rendering in progres,try later.')
    else:
        proj.SetRenderSettings({'TargetDir': latest_output_path})


def copy_xml(watch_path, source, dest):
    """
    Copy the files according to file extension, and try to replicate the original folder structure.
    Works best in conjunction with the right 'Preserve source directory levels' in Resolve render settings - Files tab.
    :param watch_path:watch folder path, where source folder is in
    :param source:source folder name
    :param dest:destination path
    :return:none
    """
    xmlpath_list = []
    for rootdir, dirs, files in os.walk(os.path.join(watch_path, source)):
        for file in files:
            # set the file extensions here
            if file.endswith(('.xml', '.fcpxml', '.aaf', '.edl')):
                xmlpath_list.append(os.path.join(rootdir, file))
    for xmlpath in xmlpath_list:
        relpath = os.path.relpath(xmlpath, watch_path)
        newpath = os.path.split(os.path.join(dest, relpath))[0]
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        try:
            shutil.copy(xmlpath, newpath)
        except:
            pass


# init Resolve handles, a script from Resolve's scripting documentation is used.
resolve = GetResolve()
if not resolve:
    sg.PopupError(
        'Cannot get Resolve API. \n Is Resolve open? '
        '\n Is "Davinci Resolve > Preference > System > General > External Scripting Using" set to "Local"?',
        title='Ahhh!!', keep_on_top=True, auto_close_duration=4,
        line_width=40,font=('Default', 15))
    exit()

pm = resolve.GetProjectManager()
proj = pm.GetCurrentProject()
mp = proj.GetMediaPool()
ms = resolve.GetMediaStorage()

# put yaml config file in the same path as the .py script
config_path = os.path.split(os.path.abspath(__file__))[0]

'''Start initialize the config'''
config = yaml_load(os.path.join(config_path, 'config.yaml'))
try:
    latest_watch_path = config['Watch path']
except:
    latest_watch_path = 'insert watch path here'

try:
    latest_output_path = config['Output path']
except:
    latest_output_path = 'insert output path here'
try:
    latest_preset = config['Preset']
except:
    latest_preset = []
try:
    copy_xml_flag = config['Copy xml']
except:
    copy_xml_flag = False
try:
    custom_preset_flag = config['Show custom presets only']
except:
    custom_preset_flag = True

get_render_presets()
if latest_preset not in preset_list:
    # If the stored preset config no longer exists in Resolve.
    latest_preset = []

# Initialize some global variables.
finished_queue = []
pending_queue = []
queue_paths = {}
xml_copied = []

# Headings of the render queue status table.
headings = ['ID', 'Timeline', 'Status', '%', 'Time']

# Uncomment below line to see more themes:
# sg.theme_previewer()
# Change to your preferred one in below line.
sg.theme('GreenTan')

sg.SetOptions(font=('Helvetica', 14))

watch_path_frame = [[sg.FolderBrowse('Browse', font=('Futura', 18), size=(6, 1), pad=(0, 5), target='WATCHPATH'),
                     sg.InputText(latest_watch_path, size=(95, 1), pad=((26, 2), 0), key='WATCHPATH',
                                  enable_events=True)
                     ]]

folder_list = [[sg.Button('Refresh', font=('Futura', 18), size=(6, 1), pad=(3, (2, 5)), key='REFRESH')],
               [sg.Listbox('', [], size=(30, 20), key='SOURCEPATHS')],
               [sg.Listbox(preset_list, size=(30, 10), key='RENDERPRESET', default_values=latest_preset,
                           enable_events=True, pad=(5, (15, 5)))],
               [sg.Checkbox('Custom only', key='CUSTOMPRESET', default=custom_preset_flag, font=('Futura', 15),
                            enable_events=True),
                sg.Button('Queue', font=('Futura', 18), size=(6, 1), pad=(3, (7, 7)),
                          key='QUEUE')]]

job_status_frame = [[sg.Table([['' for col in range(6)]], headings=headings, key='TABLE',
                              auto_size_columns=False, max_col_width=40, col_widths=[4, 31, 10, 6, 8], num_rows=28)],
                    [sg.Button('Render', font=('Futura', 18), size=(6, 1), pad=(0, (9, 7)), key='RENDER'),
                     sg.Checkbox('Copy xml', key='COPYXML', default=copy_xml_flag, enable_events=True,
                                 font=('Futura', 15),
                                 pad=(20, 0)),
                     sg.Button('Clear', font=('Futura', 18), size=(6, 1), pad=((253, 0), (9, 7)), key='CLEAR')
                     ]
                    ]

output_folder_frame = [[sg.FolderBrowse('Browse', font=('Futura', 18), size=(6, 1), pad=(0, 5), target='OUTPUTPATH'),
                        sg.InputText(latest_output_path, size=(95, 1), pad=((26, 2), 0), key='OUTPUTPATH',
                                     enable_events=True)
                        ]]

exit_frame = [[sg.Quit('Exit', font=('Futura', 18), size=(6, 1), pad=(2, 0), key='Exit')]]

col1 = sg.Column([
    [sg.Frame('Folders & Presets', folder_list, element_justification='right')]

])

col2 = sg.Column([
    [sg.Frame('Render Queue', job_status_frame, key='-QUEUE-', element_justification='left', pad=(0, (3, 0)))]])

layout = [[sg.Frame('Watch Path', watch_path_frame, pad=(20, 20))], [col1, col2],
          [sg.Frame('Output Path', output_folder_frame, pad=(20, (20, 40)))]
          # ,[sg.Frame('', exit_frame, border_width=0, pad=(20, (0,10)))]
          # uncomment if you want the 'Exit' button
          ]

window = sg.Window('FootBrake v0.2a', layout, finalize=True)

# Initialize source paths with config
if os.path.exists(latest_watch_path):
    refresh_folders(latest_watch_path)
else:
    window['WATCHPATH'](text_color='red')
    window.refresh()
if not os.path.exists(latest_output_path):
    window['OUTPUTPATH'](text_color='red')

# GUI loop and events handling
while True:
    # read PySimpleGUI window
    event, values = window.read()
    if event in (None, 'Exit'):
        yaml_config_write()
        break

    if event == 'WATCHPATH':
        if os.path.isdir(values['WATCHPATH']):
            window['WATCHPATH'](text_color='black')
            latest_watch_path = values['WATCHPATH']
            refresh_folders(latest_watch_path)
            config.update({'Watch path': latest_watch_path})
            yaml_config_write()

        else:
            window['WATCHPATH'](text_color='red')
            window['QUEUE'](disabled=True)

    if event == 'RENDERPRESET':
        latest_preset = values['RENDERPRESET'][0]
        config.update({'Render preset': latest_preset})
        yaml_config_write()

    if event == 'OUTPUTPATH':
        if os.path.isdir(values['OUTPUTPATH']):
            window['OUTPUTPATH'](text_color='black')
            latest_output_path = values['OUTPUTPATH']
            config.update({'Output path': latest_output_path})
            yaml_config_write()
        else:
            window['OUTPUTPATH'](text_color='red')

    if event == 'REFRESH':
        proj = pm.GetCurrentProject()
        mp = proj.GetMediaPool()
        if os.path.exists(latest_watch_path):
            refresh_folders(latest_watch_path)
            refresh_presets()

    if event == 'QUEUE':
        if not resolve:
            print('lost connection with Resolve API')
        elif not values['SOURCEPATHS']:
            sg.Popup('Please select a source folder.',
                     title='Select Source')
        elif not values['RENDERPRESET']:
            sg.Popup('Please select a render preset.(Create in Resolve render page first.)',
                     title='Select Preset')
        else:
            #
            try:
                proj.IsRenderingInProgress()
            except TypeError:
                proj = pm.CreateProject(f"{datetime.datetime.now():%Y%m%d_%H%M%S_}" + 'Transcode')
                mp = proj.GetMediaPool()
                # Above is needed to check if 'proj' is accessible, before checking rendering is in progress,
                # otherwise Resolve will raise an error
            if proj.IsRenderingInProgress():
                sg.Popup('Resolve rendering is in progress, go grab a coffee.', title='Rendering in progress')
            else:
                # Listbox multi-select is enabled, values['SOURCEPATHS'] is a list
                source_folders = values['SOURCEPATHS']
                for source_folder in source_folders:
                    # Avoid overwriting.
                    if latest_output_path == os.path.join(latest_watch_path, source_folder):
                        sg.popup('Output path is same to the source path for:\n\n' + latest_output_path,
                                 title='Overwriting is no fun!')
                    else:
                        # Try to import timeline, if Resolve project is switched or closed, will get 'False',
                        # then create a new project named '%timestamp%_Transcode'.
                        if not import_timeline(latest_watch_path, source_folder):
                            proj = pm.CreateProject(f"{datetime.datetime.now():%Y%m%d_%H%M%S_}" + 'Transcode')
                            mp = proj.GetMediaPool()
                            import_timeline(latest_watch_path, source_folder)

                        queue_render(latest_preset, source_folder)
                        # Below seems no longer needed.
                        # except IndexError:
                        #     sg.Popup('Please select a render preset.')

    '''Starts the event handling part.'''

    if event == 'CUSTOMPRESET':
        if values['CUSTOMPRESET']:
            custom_preset_flag = True
            config.update({'Show custom presets only': True})
        else:
            custom_preset_flag = False
            config.update({'Show custom presets only': False})
        yaml_config_write()
        refresh_presets()

    if event == 'COPYXML':
        if values['COPYXML']:
            copy_xml_flag = True
            config.update({'Copy xml': True})
        else:
            copy_xml_flag = False
            config.update({'Copy xml': False})
        yaml_config_write()

    if event == 'RENDER':
        try:
            proj.IsRenderingInProgress()
            if proj.IsRenderingInProgress():
                sg.Popup('Rendering in progres,try later.')
            elif pending_queue:
                # finally submit the render list
                proj.StartRendering(pending_queue)
                update_table_while_rendering()
                finished_queue += pending_queue
                pending_queue = []
                xml_copied = []
                queue_paths = {}
            else:
                sg.Popup('Add some jobs first.')
        # Yet there seems no need for further error handling, because the job index will be out of track anyway.
        except TypeError:
            sg.Popup('Resolve project is unreachable!')
            pending_queue = []
            finished_queue = []
            window['TABLE']([])
            window.refresh()

    if event == 'CLEAR':
        if proj.IsRenderingInProgress():
            sg.Popup('Rendering in progres,try later.')
        else:
            pending_queue = []
            finished_queue = []
            window['TABLE']([])
            window.refresh()

window.close()
