#!/usr/bin/env python
"""
Processes an rinfo string from a dsrqst to process subsets
on netcdf files.
"""

__version__ = '0.1.0'
__author__ = 'Riley Conroy (rpconroy@ucar.edu)'

import sys
import os
import logging
import pdb
import dask
import subprocess
import common
import argparse
import dsrqst_netcdf_subset

sys.path.append('/gpfs/u/home/rdadata/lib/python')
import MySubset

LOG_DIR = "/gpfs/csfs1/collections/rda/work/rpconroy/logs/" # Default log file. It should be reassigned
log_kwargs = {
        'filename' : os.path.join(LOG_DIR, "out.log"),
        'format' : '%(levelname)s:%(asctime)s:%(message)s',
        'datefmt' : '%Y-%m-%d %H:%M:%S',
        'level' : logging.DEBUG  # Can be DEBUG, INFO, WARNING, ERROR, CRITICAL
        }
default_subset_dir = "/gpfs/csfs1/collections/rda/transfer/dsrqst/"

def end_subset(message="Ending Program", errnum=1):
    """End processing and optionally provide error message and error number."""
    logging.error(message)
    exit(errnum)

def parse_rinfo_string(rinfo):
    """Parse rinfo string into more useable dict."""
    selections = {}
    rinfo_list = rinfo.split(';')
    for item in rinfo_list:
        k,v = item.split('=')
        selections[k] = v

    # Check that necessary pieces are in string and formatted correctly.
    allowed_formats = ['netcdf', 'csv']
    if 'ofmt' in selections and selections['ofmt'].lower() not in allowed_formats:
        error = 'ofmt, "'+selections['ofmt']+ '", is not correct'
        end_subet(error)

    return selections

def filter_by_tindex(param_files):
    common.wfile_in_tindex('ds131.3','fg/fg_mean_1836_CIN_sfc.nc',1)

def get_logfile_name(request_index):
    """Returns full path for logfile given request index."""
    return LOG_DIR + 'request_' + request_index + '.log'

def preprocess_rinfo(rinfo):
    """Initializes variables in rinfo if not found.
    """
    if 'datetype' not in rinfo:
        rinfo['datetype'] = 'valid_date'
    rinfo['subflag'] = get_subflag(rinfo)

    if 'elon' in rinfo:
        temp_elon = float(rinfo['elon'])
        temp_elon += 180
        rinfo['elon'] = str(temp_elon)
    if 'wlon' in rinfo:
        temp_wlon = float(rinfo['wlon'])
        temp_wlon += 180
        rinfo['wlon'] = str(temp_wlon)

    return rinfo

def get_output_filename(rindex, parameter_name, in_filename):
    """Generate output filename for subsets"""
    return rindex +'.'+ parameter_name +'.'+ os.path.basename(in_filename)


def get_subflag(rinfo):
    """Returns subflag based on rinfo parameters"""
    subflag = 0
    if 'parameters' in rinfo:
        subflag += 1
    if 'startdate' in rinfo or 'enddate' in rinfo:
        subflag += 2
    if 'nlat' in rinfo:
        subflag += 4
    return subflag

def check_csv_params(rinfo):
    """Check if csv parameters are compatible with csv subset capabilities.
    """
    if 'oformat' in rinfo and rinfo['oformat'].lower() == 'csv':
        if 'parameters' not in rinfo:
            end_subset("csv format not allowed when no parameters are selected")
        if rinfo['nlat'] != rinfo['slat'] or \
                rinfo['elon'] != rinfo['wlon']:
            end_subset("csv format not allowed for anything but single grid points")

def convert_lat(lat):
    """Confirms lat is between -90 and 90"""
    pass

def convert_lon(lon):
    """Confirms lat is between 0 and 360"""
    pass

def get_levels_needed(levels, wanted_levels):
    """Filters the levels disired from all the levels.
    """
    output_levels = []
    for level in levels:
        if level in wanted_levels:
            output_levels.append(level)
    return output_levels

def rinfo_error_check(rinfo):
    pass

def get_full_filename(dsid, filename):
    """Get the full location of data file."""
    datadir = '/gpfs/csfs1/collections/rda/data/'
    return datadir + dsid + '/' + filename

def separate_var(var):
    """Separate dsnum from variable"""
    if ':' in var:
        var = var.split(':')[1]
        return var
    return var


def subset(request_idx, request_dir=None, use_dask=True):
    """Given a request index, subsets files matching rinfo

    Args:
        request_idx (str or int): 6-digit number representing request ID.
        request_dir (str; optional): Directory to put output.

    """
    # Get request
    logging.info(f'Starting {request_idx}')
    request = common.get_request_info(request_idx)
    logging.debug(f' request: {request}')
    command = 'dsrqst_netcdf_subset.py'


    if request_dir is None:
        request_dir = os.path.join(default_subset_dir, request['request_id'])

    rinfo = common.parse_rinfo(request['rinfo'])
    rinfo = preprocess_rinfo(rinfo)
    logging.debug(f'rinfo: {rinfo}')
    dsid = common.add_ds(rinfo['dsnum'])

    rinfo_error_check(rinfo)

    for i,j in rinfo.items():
        logging.info(f'{i:15}  {j}')
    # update subflag in database
    #common.update_sflag(rinfo['subflag'], request_id)
    check_csv_params(rinfo)

    # Get tindex for each webfile;
    if not use_dask:
        partition_processing(rinfo, dsid, request_dir, request_idx)
    else:
        dask_processing(rinfo, dsid, request_dir, request_idx)


def partition_processing(rinfo, dsid, request_dir, request_idx, command):
    print('ehere')
    # define tables
    naked_dsnum = ''.join(common.add_ds(rinfo['dsnum']).split('.'))
    grid_table = naked_dsnum + '_grids2'
    web_table = naked_dsnum + '_webfiles2'

    commands = []
    total_file_size = 0
    # Params
    if 'parameters' in rinfo:
        for param in rinfo['parameters']:
            print(param)
            param_files = common.get_webfiles_by_param_and_date(
                    grid_table, param, rinfo['startdate'], rinfo['enddate'])
            #if 'tindex' in rinfo:
            #    param_files = filter_by_tindex(param_files)
            for webid_code,gridDef_code,leveltype_code,start_date,end_date,nsteps in param_files:
                in_filename = common.get_webid_from_code(web_table , webid_code)
                full_in_filename = get_full_filename(common.add_ds(rinfo['dsnum']), in_filename)

                total_file_size += os.path.getsize(f'/gpfs/csfs1/collections/rda/data/{dsid}/{in_filename}')

                if 'tindex' in rinfo and not common.wfile_in_tindex(dsid,in_filename,rinfo['tindex'][0]):
                    continue
                out_filename = get_output_filename(request_idx, separate_var(param), in_filename)
                full_out_filename = os.path.join(request_dir,out_filename)

                command_str = command +" "+ full_in_filename
                command_str += " " + full_out_filename
                command_str += " v=" + param

                command_str += ' start_date=' + rinfo['startdate']
                command_str += ' end_date=' + rinfo['enddate']

                command_str += ' nlat=' + rinfo['nlat']
                command_str += ' slat=' + rinfo['slat']
                command_str += ' elon=' + rinfo['elon']
                command_str += ' wlon=' + rinfo['wlon']


                if 'level' in rinfo and len(rinfo['level']) > 0:
                    level_codes = common.parse_levelType_code(leveltype_code)
                    wanted_levels = rinfo['level']
                    needed_levels = get_levels_needed(level_codes, wanted_levels)
                    command_str += ' levels='
                    for lev in needed_levels:
                        lev_info = common.get_level_definition(lev)
                        command_str += lev_info['value'] + ','
                    command_str = command_str [:-1]
                    commands.append({'command':command_str, 'in_file':full_in_filename, 'out_file':full_out_filename})
                else:
                    commands.append({'command':command_str, 'in_file':full_in_filename, 'out_file':full_out_filename})


    MySubset.set_dsrqst_fcount(request_idx, fcount=len(commands), isize=total_file_size)
    for command in commands:
        myrec = {}
        myrec['command'] = command['command']
        myrec['ofile'] = command['in_file']
        myrec['data_format'] = 'NetCDF4'
        MySubset.add_request_file(request_idx, command['out_file'], myrec)
        #print(command)
        #cmd_list = command.split(' ')
        #args = dict(item.split('=') for item in cmd_list[3:])
        #if 'levels' in args:
        #    args['levels'] = args['levels'].split(',')
        #request_subset.subset(cmd_list[1], cmd_list[2], **args)

def dask_processing(rinfo,dsid, request_dir, request_idx):
    # define tables
    naked_dsnum = ''.join(common.add_ds(rinfo['dsnum']).split('.'))
    grid_table = naked_dsnum + '_grids2'
    web_table = naked_dsnum + '_webfiles2'

    lazy_results = []
    total_file_size = 0
    # Params
    if 'parameters' in rinfo:
        for param in rinfo['parameters']:
            logging.info(param)
            param_files = common.get_webfiles_by_param_and_date(
                    grid_table, param, rinfo['startdate'], rinfo['enddate'])
            #if 'tindex' in rinfo:
            #    param_files = filter_by_tindex(param_files)
            for webid_code,gridDef_code,leveltype_code,start_date,end_date,nsteps in param_files:
                in_filename = common.get_webid_from_code(web_table , webid_code)
                full_in_filename = get_full_filename(common.add_ds(rinfo['dsnum']), in_filename)

                total_file_size += os.path.getsize(f'/gpfs/csfs1/collections/rda/data/{dsid}/{in_filename}')

                if 'tindex' in rinfo and not common.wfile_in_tindex(dsid,in_filename,rinfo['tindex'][0]):
                    continue
                out_filename = get_output_filename(request_idx, separate_var(param), in_filename)
                full_out_filename = os.path.join(request_dir,out_filename)

                subset_params=[]
                subset_params.append(full_in_filename)
                subset_params.append(full_out_filename)
                cur_subset_params={}
                cur_subset_params['v'] = param
                cur_subset_params['start_date'] = rinfo['startdate']
                cur_subset_params['end_date'] = rinfo['enddate']
                cur_subset_params['nlat'] = rinfo['nlat']
                cur_subset_params['slat'] = rinfo['slat']
                cur_subset_params['elon'] = rinfo['elon']
                cur_subset_params['wlon'] = rinfo['wlon']

                if 'level' in rinfo and len(rinfo['level']) > 0:
                    level_codes = common.parse_levelType_code(leveltype_code)
                    wanted_levels = rinfo['level']
                    needed_levels = get_levels_needed(level_codes, wanted_levels)
                    if len(needed_levels) == 0:
                        continue
                    levs = []
                    for lev in needed_levels:
                        lev_info = common.get_level_definition(lev)
                        levs.append(lev_info['value'])
                    cur_subset_params['levels'] = levs

                lazy_result = dask.delayed(dsrqst_netcdf_subset.subset)(full_in_filename, full_out_filename, **cur_subset_params)
                lazy_results.append(lazy_result)
                # serial processing
                #dsrqst_netcdf_subset.subset(full_in_filename, full_out_filename, **cur_subset_params)
    print(lazy_results)
    dask.compute(*lazy_results)





    #MySubset.set_dsrqst_fcount(request_idx, fcount=len(commands), isize=total_file_size)

    #for command in commands:
    #    myrec = {}
    #    myrec['command'] = command['command']
    #    myrec['ofile'] = command['in_file']
    #    myrec['data_format'] = 'NetCDF4'
    #    MySubset.add_request_file(request_idx, command['out_file'], myrec)
    #    #print(command)
    #    #cmd_list = command.split(' ')
    #    #args = dict(item.split('=') for item in cmd_list[3:])
    #    #if 'levels' in args:
    #    #    args['levels'] = args['levels'].split(',')
    #    #request_subset.subset(cmd_list[1], cmd_list[2], **args)

def parse_args(args):
    parser = argparse.ArgumentParser(
                    prog='dsrqst_netcdf_commandlist',
                    description='Subsets netcdf files from the rda given an `rinfo string and outdir')
    parser.add_argument('rindex', help = '6 digit dsrqst rindex')
    parser.add_argument('outdir', help = 'Location where subsetted files should be output')
    parser.add_argument('-ld','--logdir', help = "Change where log file is stored")
    parser.add_argument('-ll','--loglevel',
            help = "log level for this run. May be DEBUG, INFO, WARNING, ERROR")
    parser.add_argument('-ud','--use_dask', action='store_true', help="Use dask for multiprocessing")
    args = parser.parse_args()
    return args

def main():
    """Set up subsetting."""
    if len(sys.argv) == 1:
        logging.basicConfig(**log_kwargs)
        logging.warning("Not enough arguments")
        exit(1)
    args = parse_args(sys.argv[1:])
    if args.loglevel is not None:
        if args.loglevel not in logging.getLevelNamesMapping():
            print(f'loglevel: {args.loglevel} not in {logging.getLevelNamesMapping().keys()}')
            print('Using default loglevel')
        else:
            log_kwargs['level'] = args.loglevel
    if args.logdir is not None:
        try:
            os.stat(args.logdir)
            log_kwargs['filename'] = os.path.join(args.log_dir, "log.log"),
        except FileNotFoundError:
            print(f'Directory, {args.logdir}, does not exist. Using {LOG_DIR}.')

    log_name = f'dsrqst_{args.rindex}.log'
    log_kwargs['filename'] = os.path.join(LOG_DIR, log_name)
    logging.basicConfig(**log_kwargs)
    logging.debug(f'Parsed args sucessfully. args: {args}')

    subset(args.rindex, args.outdir, use_dask=args.use_dask)

if __name__ == '__main__':
    """Calls subset if from command line"""
    main()

