import PySimpleGUIWeb as sg
import os
import shutil
import datetime
import time
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


def refresh_presets():
    if values['CUSTOMPRESET']:
        preset_list = list(proj.GetRenderPresets().values())[19:len(proj.GetRenderPresets())]
    else:
        preset_list = list(proj.GetRenderPresets().values())[0:len(proj.GetRenderPresets())]
    window['RENDERPRESET'](preset_list)
    window.refresh()
    return preset_list


def refresh_folders(watch_path):
    path_list = []
    for item in os.listdir(watch_path):
        if os.path.isdir(os.path.join(watch_path, item)):
            path_list.append(item)
    window['SOURCEPATHS'](path_list)
    window.refresh()

def refresh_outputfolder(output_path):
    path_list = []
    for item in os.listdir(output_path):
        if os.path.isdir(os.path.join(output_path, item)):
            path_list.append(item)
    window['OUTPUTSUB'](path_list)
    window.refresh()

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
    status_table = []
    for k in sorted(set(finished_queue + pending_queue)):
        try:
            status = proj.GetRenderJobStatus(k)
            status.update({'Idx': k, 'Name': proj.GetRenderJobs()[k]['TimelineName']})
            status_table += [
                'Job ' + str(status.get('Idx', 'Unknown')) + '---' + str(status.get('Name', 'Unknown')) + '---' +
                str(status.get('JobStatus', 'Unknown')) + '---' + str(status.get('CompletionPercentage', 'NA'))
                + '---' + str(datetime.timedelta(milliseconds=status.get('TimeTakenToRenderInMs', 0))).split('.', 2)[0]]
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
            queue_paths.update({new_job_idx: [values['WATCHPATH'], queue_source_folder, latest_output_path]})
            update_render_status()
        else:
            sg.Popup('Failed to add render job, check Resolve.')
    else:
        sg.Popup('Failed to add render job, empty folder?')


def update_table_while_rendering():
    """
        Continuously get render status of all the jobs, finished and ongoing, from Resolve, and update the GUI.
        :return: none
        """
    while proj.IsRenderingInProgress():
        update_render_status()
        # update info every 0.5 second
        time.sleep(0.5)
        if values['COPYXML']:
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


# init Resolve handles
resolve = GetResolve()
pm = resolve.GetProjectManager()
proj = pm.GetCurrentProject()
mp = proj.GetMediaPool()
ms = resolve.GetMediaStorage()

# def  get directory list
status_table = []
finished_queue = []
queue_paths={}
pending_queue = []
xml_copied = []
preset_list = list(proj.GetRenderPresets().values())[19:len(proj.GetRenderPresets())]
headings = ['ID', 'Timeline', 'Status', '%', 'Time']

sg.theme('GreenTan')

sg.SetOptions(font=('Helvetica', 14))

'''PC OPTIMIZED
Below is obsolete, don't use.
'''
# col1 = sg.Column([
#     [sg.Button('Folder Refresh',font=('Futura', 18), key='REFRESH')],
#     [sg.Listbox('', [], size=(400, 800), key='SOURCEPATHS', enable_events=True)]
# ])
#
# col2 = sg.Column([
#     [sg.Button('Refresh Preset', font=('Futura', 18), key='REFRESHPR')],
#     [sg.Listbox(preset_list, key='RENDERPRESET', size=(300, 800))],
# ])
#
# col3 = sg.Column([
#     [sg.Button('Queue', font=('Futura', 18), key='QUEUE')],
#     [sg.Listbox('', [], key='TABLE', size=(600, 800), )],
# ])
#
# col4 = sg.Column([
#     [sg.Button('Render', font=('Futura', 18),pad=(0,100), size=(300,100),key='RENDER')],
#     [sg.Button('ABORT', font=('Futura', 18),button_color='yellow', key='QUEUE',pad=(0,(450,0)))]
# ])
# layout = [[sg.Frame('Watch Folder',[]),sg.InputText('', size=(65, 1), key='WATCHPATH')],[col1, col2, col3,col4]]

"""CELLPHONE"""
col1 = sg.Column([
    [sg.Button('Refresh Source', font=('Futura', 18), key='REFRESH')],
    [sg.Listbox('', [], size=(360, 200), key='SOURCEPATHS', enable_events=True)]
])

col2 = sg.Column([
    [sg.Button('Refresh Presets', font=('Futura', 18), key='REFRESHPR')],
    [sg.Checkbox('Custom only', key='CUSTOMPRESET', default=True, font=('Futura', 15))],
    [sg.Listbox(preset_list, key='RENDERPRESET', size=(360, 100))]
])

col3 = sg.Column([
    [sg.Button('Queue', font=('Futura', 18), key='QUEUE'), sg.Button('Clear', font=('Futura', 18), key='CLEAR')],
    [sg.Listbox('', [], key='TABLE', size=(360, 200), )],
])

col5 = sg.Column([
    [sg.Button('Render', font=('Futura', 18), pad=(5, 5), size=(360, 100), key='RENDER')],
    [sg.Button('List Folders in Destination', font=('Futura', 18), key='REFRESHOUTPUT')],
    [sg.Listbox('', [], size=(360, 200), key='OUTPUTSUB', enable_events=True)],
    [sg.Button('ABORT', font=('Futura', 18), button_color='yellow', key='ABORT', pad=(305, 5))]
])

col4 = sg.Column([
    [
     sg.Checkbox('Copy xml', key='COPYXML', default=True, font=('Futura', 15))]
])
layout = [[sg.InputText('', size=(36, 1), key='WATCHPATH')],
          [col1], [col2], [col3], [col4],
          [sg.InputText('', size=(36, 1), key='OUTPUTPATH')],
          [col5]]

# must include disable_close=True to let the server run in background
window = sg.Window('Resolve Transkode v0.1a', layout, web_port=29259, finalize=True, disable_close=True)
window['WATCHPATH'].update('/Users/')

while True:
    # read PySimpleGUI window
    event, values = window.read()


    if event == 'SOURCEPATHS':
        print('listbox event!')



    if event == 'REFRESH':
        print('refresh event!')
        if os.path.exists(values['WATCHPATH']):
            refresh_folders(values['WATCHPATH'])

    if event == 'REFRESHOUTPUT':
        print('REFRESHOUTPUT event!')
        if os.path.exists(values['OUTPUTPATH']):
            refresh_outputfolder(values['OUTPUTPATH'])

    if event == 'REFRESHPR':
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
                sg.Popup('Resolve still rendering, go grab a coffee.')
            else:
                watch_path = values['WATCHPATH']
                source_folders = values['SOURCEPATHS']
                for source_folder in source_folders:
                    # Avoid overwriting.
                    if values['OUTPUTPATH'] == os.path.join(watch_path, source_folder):
                        sg.popup('Output path is same to the source path for:\n\n' + latest_output_path)
                    elif not os.path.exists(os.path.join(watch_path, source_folder)):
                        sg.Popup('Source path error, please check!')
                        window['WATCHPATH'](text_color='red')
                    else:
                        # Try to import timeline, if Resolve project is switched or closed, will get 'False',
                        # then create a new project named '%timestamp%_Transcode'.
                        if not import_timeline(values['WATCHPATH'], source_folder):
                            proj = pm.CreateProject(f"{datetime.datetime.now():%Y%m%d_%H%M%S_}" + 'Transcode')
                            mp = proj.GetMediaPool()
                            import_timeline(watch_path, source_folder)
                        try:
                            queue_render(values['RENDERPRESET'][0], os.path.join(watch_path, source_folder))
                        except IndexError:
                            sg.Popup('Please select a render preset.')

    if event == 'CLEAR':
        if proj.IsRenderingInProgress():
            sg.Popup('Rendering in progres,try later.')
        else:
            pending_queue = []
            finished_queue = []
            window['TABLE']([])
            window.refresh()

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
                xml_copied = []
                pending_queue = []
            else:
                sg.Popup('Add some jobs first.')
        # Yet there seems no need for further error handling, because the job index will be out of track anyway.
        except TypeError:
            sg.Popup('Resolve project is unreachable!')
            pending_queue = []
            finished_queue = []
            window['TABLE']([])
            window.refresh()
    if event == 'ABORT':
        proj.StopRendering()
        pending_queue = []
        finished_queue = []
        window['TABLE']([])
        window.refresh()
