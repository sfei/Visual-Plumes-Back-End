import csv, io, os, sys, json, math, glob, zipfile
import traceback
from io import StringIO 
from datetime import datetime
from django.http import HttpResponse, Http404, JsonResponse, FileResponse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

# Not in use, attempt to add repo path to python system paths
# sys.path.append("C:\\Users\\ltflo\\Documents\\SFEI\\repos")

from . import model_um3

TMP_FILE_PATH = os.path.join("tmp")

def parse_vp_float(val):
  if val == '' or val == None:
    return None
  else:
    return float(val)

def parse_vp_int(val):
  if val == '' or val == None:
    return None
  else:
    return int(val)

def index(request):
    
    print(request)
    
    json_response = {
      "message":"Success!"
    }

    return JsonResponse(json_response, status=200, safe=False)

def get_unit(unit):
  """
    Convert string units to their respective types.
  """
  match unit:
    # Length
    case "m":
      return model_um3.units.Length.METERS
    case "cm":
      return model_um3.units.Length.CENTIMETERS
    case "ft":
      return model_um3.units.Length.FEET
    case "in":
      return model_um3.units.Length.INCHES
    case "fath":
      return model_um3.units.Length.FATHOMS
    
    # Speed
    case "m/s":
      return model_um3.units.Speed.METERS_PER_SECOND
    case "cm/s":
      return model_um3.units.Speed.CENTIMETERS_PER_SECOND
    case "ftm/s":
      return model_um3.units.Speed.FATHOMS_PER_SECOND
    case "kts":
      return model_um3.units.Speed.KNOTS
    case "mph":
      return model_um3.units.Speed.MILES_PER_HOUR
    case "ft/s":
      return model_um3.units.Speed.FEET_PER_SECOND
    
    # Angle
    case "deg":
      return model_um3.units.Angle.DEGREES
    case "rad":
      return model_um3.units.Angle.RADIANS
    case "Surv-deg":
      return model_um3.units.Angle.N_DEGREES
    case "Surv-rad":
      return model_um3.units.Angle.N_RADIANS
    
    # Time
    case "s":
      return model_um3.units.Time.SECONDS
    case "min":
      return model_um3.units.Time.MINUTES
    case "hr":
      return model_um3.units.Time.HOURS
    case "d":
      return model_um3.units.Time.DAYS
    
    # Flow
    case "MGD":
      return model_um3.units.FlowRate.MEGAGALLONS_PER_DAY
    case "m3/s":
      return model_um3.units.FlowRate.CUBIC_METERS_PER_SECOND
    case "MLD":
      return model_um3.units.FlowRate.MEGALITERS_PER_DAY
    case "ft3/s":
      return model_um3.units.FlowRate.CUBIC_FEET_PER_SECOND
    case "bbl/d":
      return model_um3.units.FlowRate.BARRELS_PER_DAY
    
    # Salinity
    case 'psu':
      return model_um3.units.Salinity.PRACTICAL_SALINITY_UNITS
    case 'mmho/cm':
      return model_um3.units.Salinity.MILLIMHO_PER_CENTIMETER
    case 'kg/m3':
      return model_um3.units.Salinity.KILOGRAMS_PER_CUBIC_METER
    case 'sigmaT':
      return model_um3.units.Salinity.SIGMA_T
    case 'lb/ft3':
      return model_um3.units.Salinity.POUNDS_PER_CUBIC_FOOT
    
    
    # Concentration
    case 'ppm':
      return model_um3.units.Concentration.PARTS_PER_MILLION
    case 'kg/kg':
      return model_um3.units.Concentration.KILOGRAM_PER_KILOGRAM
    case 'ppb':
      return model_um3.units.Concentration.PARTS_PER_BILLION
    case '%':
      return model_um3.units.Concentration.PERCENT
    case 'col/dl':
      return model_um3.units.Concentration.COLONIES_PER_100ML

    # Isopleth
    case 'concent':
      return model_um3.units.Isopleth.CONCENTRATION
    case 'salinity':
      return model_um3.units.Isopleth.SALINITY
    case 'temp':
      return model_um3.units.Isopleth.TEMPERATURE
    case 'speed':
      return model_um3.units.Isopleth.SPEED

    # Temperature
    case 'C':
      return model_um3.units.Temperature.CELSIUS
    case 'F':
      return model_um3.units.Temperature.FAHRENHEIT
    case 'K':
      return model_um3.units.Temperature.KELVIN

    # DecayRate
    case 's-1':
      return model_um3.units.DecayRate.PER_SECOND
    case 'd-1':
      return model_um3.units.DecayRate.PER_DAY
    case 'T90hr':
      return model_um3.units.DecayRate.T90_HOUR
    case 'ly/hr':
      return model_um3.units.DecayRate.LY_PER_HOUR
    case 'hr-1':
      return model_um3.units.DecayRate.PER_HOUR
    
    # Unitless
    case '':
      return model_um3.units.Unitless.UNITLESS
    
    case _:
      return model_um3.units.Unitless.UNITLESS

def get_similarity_profile(val):
  """"
    Obtain similarity profile type.
  """
  if val == 'power':
    return model_um3.params.ModelParameters.SimilarityProfile.POWER_3_2
  elif val == 'gaussian':
     return model_um3.params.ModelParameters.SimilarityProfile.GAUSSIAN
  else:
    return model_um3.params.ModelParameters.SimilarityProfile.DEFAULT

def get_ff_diffusivity_type(val):
  """
  Obtain far field diffusivity enumberated type.
  """
  if val == 'CONSTANT':
    return model_um3.params.ModelParameters.FarfieldDiffusivity.CONSTANT
  elif val == '':
    return model_um3.params.ModelParameters.FarfieldDiffusivity.POWER_4_3
  else:
   return model_um3.params.ModelParameters.FarfieldDiffusivity.DEFAULT

def list2tuple(list):
  """
    Return a list as a tuple.
  """
  return tuple(i for i in list)

def load_model_params(post_data):
  """
    Load model input data.
  """
  debug = False

  # Initialize model parameter object
  model_params  = model_um3.params.ModelParameters.ModelParameters()

  def get_max_reversals(val):
    match val:
      case "INITIAL_TRAP_LEVEL":
        return model_um3.params.ModelParameters.MaxVerticalReversals.INITIAL_TRAP_LEVEL
      case "MAX_RISE_OR_FALL":
        return model_um3.params.ModelParameters.MaxVerticalReversals.MAX_RISE_OR_FALL
      case "SECOND_TRAP_LEVEL":
        return model_um3.params.ModelParameters.MaxVerticalReversals.SECOND_TRAP_LEVEL
      case "SECOND_MAX_RISE_OR_FALL":
        return model_um3.params.ModelParameters.MaxVerticalReversals.SECOND_MAX_RISE_OR_FALL
  
  def get_bacterial_model(val):
    match val:
      case "mancini":
        return model_um3.params.ModelParameters.BacteriaModel.COLIFORM_MANCINI
      case "coliform":
        return model_um3.params.ModelParameters.BacteriaModel.COLIFORM_301H
      case "enterococcus":
        return model_um3.params.ModelParameters.BacteriaModel.ENTEROCCOUS_301H

  model_params.report_effective_dillution = post_data['reportEffectiveDillution']
  model_params.current_vector_averaging   = post_data['currentVectorAveraging']
  model_params.write_step_freq            = parse_vp_int(post_data['writeStepFreq'])
  model_params.max_reversals              = get_max_reversals(post_data['maxReverals'])
  model_params.stop_on_bottom_hit         = post_data['stopOnBottomHit'] == 'true'
  model_params.dont_stop_on_surface_hit   = post_data['dontStopOnSurfaceHit'] == 'true'
  model_params.allow_induced_current      = post_data['allowInducedCurrent'] == 'true'
  model_params.max_dilution               = parse_vp_int(post_data['maxDilutionReported'])

  # model parameters (equation parameters)
  # print(f"post_data['diffPortContCoeff']: {post_data['diffPortContCoeff']}")
  if post_data['diffPortContCoeff'] != '' and  post_data['diffPortContCoeff'] != None:
    model_params.contraction_coeff          = parse_vp_float(post_data['diffPortContCoeff'])

  if post_data['lightAbsorpCoeff'] != '' and post_data['lightAbsorpCoeff'] != None:
    model_params.light_absorb_coeff         = parse_vp_float(post_data['lightAbsorpCoeff'])

  if post_data['um3AspCoeff'] != '' and post_data['um3AspCoeff'] != None:
    model_params.aspiration_coeff           = parse_vp_float(post_data['um3AspCoeff'])

  model_params.bacteria_model             = get_bacterial_model(post_data['bacterialModelValue'])
  model_params.at_equilibrium             = post_data['eqOfState'] == 'S_T' # true means equation of state considers S,T (no pressure)
  model_params.similarity_profile         = get_similarity_profile(post_data['similarityProfile'])
 
  # model parameters (far-field model)
  model_params.brooks_far_field           = post_data['modelConfigType'] == 'brooks'
  model_params.estimate_ff_background     = post_data['estimateFarfieldBackground']
  model_params.output_all_ff_increments   = post_data['outputAllFarfieldTimeIncrements']
  model_params.farfield_diffusivity       = get_ff_diffusivity_type(post_data['farfieldDiffusivity'])
  model_params.ff_increment               = parse_vp_float(post_data['farfieldCoeff'])

  # Tidal Pollution Buildup

  model_params.tidal_pollution_buildup    = post_data['modelConfigType'] == 'tidal'

  if post_data['tidalPollutantBuildup']['channel_width'] != '':
    model_params.tpb_channel_width = parse_vp_float(post_data['tidalPollutantBuildup']['channel_width'])
  else:
    model_params.tpb_channel_width = 100

  if post_data['tidalPollutantBuildup']['segment_length'] != '':
    model_params.tpb_segment_length = parse_vp_float(post_data['tidalPollutantBuildup']['segment_length'])
  
  if post_data['tidalPollutantBuildup']['upstream_dir'] != '':
    model_params.tpb_upstream_dir = parse_vp_float(post_data['tidalPollutantBuildup']['upstream_dir'])

  if post_data['tidalPollutantBuildup']['coast_bin'] != '':
    model_params.tpb_coast_bin = parse_vp_int(post_data['tidalPollutantBuildup']['coast_bin'])

  if post_data['tidalPollutantBuildup']['coast_concentration'] != '':
    model_params.tpb_coast_concentration = parse_vp_float(post_data['tidalPollutantBuildup']['coast_concentration'])

  if post_data['tidalPollutantBuildup']['mixing_zone_ceil'] != '':
    model_params.tpb_mixing_zone_ceil = parse_vp_float(post_data['tidalPollutantBuildup']['mixing_zone_ceil'])

  # Shore Vector
  model_params.use_shore_vector = post_data['useShoreVector']
  model_params.dist_to_shore    = parse_vp_float(post_data['distToShore'])
  model_params.dir_to_shore     = parse_vp_float(post_data['dirToShore'])

  if debug:
    print("Model Parameters:")
    print(f"model_params.tpb_coast_bin             :{model_params.tpb_coast_bin}")
    print(f"model_params.report_effective_dillution:{model_params.report_effective_dillution}")
    print(f"model_params.current_vector_averaging  :{model_params.current_vector_averaging  }")
    print(f"model_params.write_step_freq           :{model_params.write_step_freq           }")
    print(f"model_params.max_reversals             :{model_params.max_reversals             }")
    print(f"model_params.stop_on_bottom_hit        :{model_params.stop_on_bottom_hit        }")
    print(f"model_params.dont_stop_on_surface_hit  :{model_params.dont_stop_on_surface_hit  }")
    print(f"model_params.allow_induced_current     :{model_params.allow_induced_current     }")
    print(f"model_params.max_dilution              :{model_params.max_dilution              }")
    print(f"model_params.contraction_coeff         :{model_params.contraction_coeff         }")
    print(f"model_params.light_absorb_coeff        :{model_params.light_absorb_coeff        }")
    print(f"model_params.aspiration_coeff          :{model_params.aspiration_coeff          }")
    print(f"model_params.bacteria_model            :{model_params.bacteria_model            }")
    print(f"model_params.at_equilibrium            :{model_params.at_equilibrium            }")
    print(f"model_params.similarity_profile        :{model_params.similarity_profile        }")
    print(f"model_params.brooks_far_field          :{model_params.brooks_far_field          }")
    print(f"model_params.tidal_pollution_buildup   :{model_params.tidal_pollution_buildup   }")
    print(f"model_params.tpb_channel_width         :{model_params.tpb_channel_width         }")
    print(f"model_params.farfield_diffusivity         :{model_params.farfield_diffusivity         }")

  return model_params

def load_diffuser_store(data):
  """
    Load Diffuser store input data. 
  """
  debug = False

  # Initialize diffuser store object
  diff_store    = model_um3.params.DiffuserStore.DiffuserStore()

  # Get enumerated unit values
  diff_store.diameter.units            = get_unit(data['diffuserStore']['port_diameter']['value'])
  diff_store.offset_x.units            = get_unit(data['diffuserStore']['source_x_coord']['value'])
  diff_store.offset_y.units            = get_unit(data['diffuserStore']['source_y_coord']['value'])
  diff_store.vertical_angle.units      = get_unit(data['diffuserStore']['vertical_angle']['value'])
  diff_store.horizontal_angle.units    = get_unit(data['diffuserStore']['horizontal_angle']['value'])
  diff_store.num_ports.units           = get_unit(data['diffuserStore']['num_of_ports']['value'])
  diff_store.acute_mixing_zone.units   = get_unit(data['diffuserStore']['mix_zone_distance']['value'])
  diff_store.isopleth.units            = get_unit(data['diffuserStore']['isopleth_val']['value'])
  diff_store.depth.units               = get_unit(data['diffuserStore']['port_depth']['value'])
  diff_store.effluent_flow.units       = get_unit(data['diffuserStore']['effluent_flow']['value'])
  diff_store.salinity.units            = get_unit(data['diffuserStore']['effluent_salinity']['value'])
  diff_store.temperature.units         = get_unit(data['diffuserStore']['effluent_temp']['value'])
  diff_store.concentration.units       = get_unit(data['diffuserStore']['effluent_conc']['value'])
  diff_store.port_spacing.units        = get_unit(data['diffuserStore']['port_spacing']['value'])

  if debug:
    print("Diffuser Store (diff_store):")
    print(f"diff_store.diameter.units          : {diff_store.diameter.units         }")
    print(f"diff_store.offset_x.units          : {diff_store.offset_x.units         }")
    print(f"diff_store.offset_y.units          : {diff_store.offset_y.units         }")
    print(f"diff_store.vertical_angle.units    : {diff_store.vertical_angle.units   }")
    print(f"diff_store.horizontal_angle.units  : {diff_store.horizontal_angle.units }")
    print(f"diff_store.num_ports.units         : {diff_store.num_ports.units        }")
    print(f"diff_store.port_spacing.units      : {diff_store.port_spacing.units        }")
    print(f"diff_store.acute_mixing_zone.units : {diff_store.acute_mixing_zone.units}")
    print(f"diff_store.isopleth.units          : {diff_store.isopleth.units         }")
    print(f"diff_store.depth.units             : {diff_store.depth.units            }")
    print(f"diff_store.effluent_flow.units     : {diff_store.effluent_flow.units    }")
    print(f"diff_store.salinity.units          : {diff_store.salinity.units         }")
    print(f"diff_store.temperature.units       : {diff_store.temperature.units      }")
    print(f"diff_store.concentration.units     : {diff_store.concentration.units    }")

  return diff_store

def load_diffuser_params(data_row, diff_timeseries_files):
  """
    Populate Diffuser store parameters, omit fields for which time series data are present.
  """
  debug = False

  # Initiate parameters
  diff_params   = model_um3.params.DiffuserParameters.DiffuserParameters()

  # Non-time series fields
  diff_params.diameter          = parse_vp_float(data_row['port_diameter'])
  diff_params.offset_x          = parse_vp_float(data_row['source_x_coord'])
  diff_params.offset_y          = parse_vp_float(data_row['source_y_coord'])
  diff_params.vertical_angle    = parse_vp_float(data_row['vertical_angle'])
  diff_params.horizontal_angle  = parse_vp_float(data_row['horizontal_angle'])
  diff_params.num_ports         = parse_vp_float(data_row['num_of_ports'])
  diff_params.acute_mixing_zone = parse_vp_float(data_row['mix_zone_distance'])
  diff_params.isopleth          = parse_vp_float(data_row['isopleth_val'])
  diff_params.depth             = parse_vp_float(data_row['port_depth'])

  # Potential time series fields
  diff_params.port_spacing      = parse_vp_float(data_row['port_spacing'])
  diff_params.effluent_flow     = parse_vp_float(data_row['effluent_flow'])
  diff_params.salinity          = parse_vp_float(data_row['effluent_salinity'])
  diff_params.temperature       = parse_vp_float(data_row['effluent_temp'])
  diff_params.concentration     = parse_vp_float(data_row['effluent_conc'])

  # if not (data_row['port_spacing'] == None or data_row['port_spacing'] == ''):
  #   diff_params.port_spacing      = float(data_row['port_spacing'])
  
  # if (diff_timeseries_files['effluent_flow'] == None or diff_timeseries_files['effluent_flow'] == ''):
  #   diff_params.effluent_flow     = float(data_row['effluent_flow'])

  # if (diff_timeseries_files['effluent_salinity'] == None or diff_timeseries_files['effluent_salinity'] == ''):
  #   diff_params.salinity          = float(data_row['effluent_salinity'])
  
  # if (diff_timeseries_files['effluent_temp'] == None or diff_timeseries_files['effluent_temp'] == ''):
  #   diff_params.temperature       = float(data_row['effluent_temp'])

  # if (diff_timeseries_files['effluent_concentration'] == None or diff_timeseries_files['effluent_concentration'] == ''):
  #   diff_params.concentration     = float(data_row['effluent_conc'])

  if debug:
    print("Diffuser parameters (diff_params):")
    print(f"diff_params.diameter         : {diff_params.diameter         }" )
    print(f"diff_params.offset_x         : {diff_params.offset_x         }" )
    print(f"diff_params.offset_y         : {diff_params.offset_y         }" )
    print(f"diff_params.vertical_angle   : {diff_params.vertical_angle   }" )
    print(f"diff_params.horizontal_angle : {diff_params.horizontal_angle }" )
    print(f"diff_params.num_ports        : {diff_params.num_ports        }" )
    print(f"diff_params.acute_mixing_zone: {diff_params.acute_mixing_zone}" )
    print(f"diff_params.isopleth         : {diff_params.isopleth         }" )
    print(f"diff_params.depth            : {diff_params.depth            }" )
    print(f"diff_params.effluent_flow    : {diff_params.effluent_flow    }" )
    print(f"diff_params.salinity         : {diff_params.salinity         }" )
    print(f"diff_params.temperature      : {diff_params.temperature      }" )
    print(f"diff_params.concentration    : {diff_params.concentration    }" )

  return diff_params

def load_ambient_store(data):
  """
    Populate Ambient Data store
  """
  debug = False

  ambient_store = model_um3.ambient.AmbientStore.AmbientStore()

  ambient_store.z.z_is_depth        = data['depth_or_height']['z_is_depth']
  ambient_store.z.units             = get_unit(data['depth_or_height']['mu'])
  ambient_store.current_speed.units = get_unit(data['current_speed']['mu'])
  ambient_store.current_dir.units   = get_unit(data['current_direction']['mu'])
  ambient_store.salinity.units      = get_unit(data['ambient_salinity']['mu'])
  ambient_store.temperature.units   = get_unit(data['ambient_temperature']['mu'])
  ambient_store.bg_conc.units       = get_unit(data['background_concentration']['mu'])
  ambient_store.decay_rate.units    = get_unit(data['pollution_decay_rate']['mu'])
  ambient_store.ff_velocity.units   = get_unit(data['far_field_curr_speed']['mu'])
  ambient_store.ff_dir.units        = get_unit(data['far_field_curr_dir']['mu'])
  ambient_store.ff_diff_coeff.units = get_unit(data['far_field_diff_coeff']['mu'])

  if debug:
    print("Ambient Store Units:")
    print(f"ambient_store.z.z_is_depth       : {ambient_store.z.z_is_depth}")
    print(f"ambient_store.z.units            : {ambient_store.z.units}")
    print(f"ambient_store.current_speed.units: {ambient_store.current_speed.units}")
    print(f"ambient_store.current_dir.units  : {ambient_store.current_dir.units  }")
    print(f"ambient_store.salinity.units     : {ambient_store.salinity.units     }")
    print(f"ambient_store.temperature.units  : {ambient_store.temperature.units  }")
    print(f"ambient_store.bg_conc.units      : {ambient_store.bg_conc.units      }")
    print(f"ambient_store.decay_rate.units   : {ambient_store.decay_rate.units   }")
    print(f"ambient_store.ff_velocity.units  : {ambient_store.ff_velocity.units  }")
    print(f"ambient_store.ff_dir.units       : {ambient_store.ff_dir.units       }")
    print(f"ambient_store.ff_diff_coeff.units: {ambient_store.ff_diff_coeff.units}")

  return ambient_store

def load_ambient_data(ambient_row,ambient_timeseries_files):
  """
    Load ambient input data, omit fields for which timeseries files are present.
  """
  debug = False

  ambient_data = model_um3.ambient.Ambient.Ambient()

  if debug:
    print(f"depth_or_height         : {ambient_row['depth_or_height']            }")
    print(f"current_speed           : {ambient_row['current_speed'] }")
    print(f"current_direction       : {ambient_row['current_direction']          }")
    print(f"ambient_salinity        : {ambient_row['ambient_salinity']           }")
    print(f"ambient_temperature     : {ambient_row['ambient_temperature']        }")
    print(f"background_concentration: {ambient_row['background_concentration']   }")
    print(f"pollution_decay_rate    : {ambient_row['pollution_decay_rate']       }")
    print(f"far_field_curr_speed    : {ambient_row['far_field_curr_speed']       }")
    print(f"far_field_curr_dir      : {ambient_row['far_field_curr_dir']         }")
    print(f"far_field_diff_coeff    : {ambient_row['far_field_diff_coeff']       }")

  ambient_data.z             = parse_vp_float(ambient_row['depth_or_height'])

  # print(f"ambient_timeseries_files['current_speed']: {ambient_timeseries_files['current_speed']}")
  if (ambient_timeseries_files['current_speed'] == None or ambient_timeseries_files['current_speed'] == ''):
    if not (ambient_row['current_speed'] == None or ambient_row['current_speed'] == ''):
      ambient_data.current_speed = parse_vp_float(ambient_row['current_speed'])

  if (ambient_timeseries_files['current_direction'] == None or ambient_timeseries_files['current_direction'] == ''):
    if not ( ambient_row['current_direction'] == None or ambient_row['current_direction'] == ''):
      ambient_data.current_dir   = parse_vp_float(ambient_row['current_direction'])
  
  if ambient_timeseries_files['ambient_salinity'] == None:
    if not ( ambient_row['ambient_salinity'] == None or ambient_row['ambient_salinity'] == ''):
      ambient_data.salinity      = parse_vp_float(ambient_row['ambient_salinity'])

  if ambient_timeseries_files['ambient_temperature'] == None:
    if not ( ambient_row['ambient_temperature'] == None or ambient_row['ambient_temperature'] == ''):
      ambient_data.temperature   = parse_vp_float(ambient_row['ambient_temperature'])
  
  if ambient_timeseries_files['background_concentration'] == None:
    if not ( ambient_row['background_concentration'] == None or ambient_row['background_concentration'] == ''):
      ambient_data.bg_conc       = parse_vp_float(ambient_row['background_concentration'])

  if ambient_timeseries_files['pollution_decay_rate'] == None:
    if not ( ambient_row['pollution_decay_rate'] == None or ambient_row['pollution_decay_rate'] == ''):
      ambient_data.decay_rate    = parse_vp_float(ambient_row['pollution_decay_rate'])

  if ambient_timeseries_files['far_field_curr_speed'] == None:
    if not ( ambient_row['far_field_curr_speed'] == None or ambient_row['far_field_curr_speed'] == ''):
      ambient_data.ff_velocity   = parse_vp_float(ambient_row['far_field_curr_speed'])

  if ambient_timeseries_files['far_field_curr_dir'] == None:
    if not ( ambient_row['far_field_curr_dir'] == None or ambient_row['far_field_curr_dir'] == ''):
      ambient_data.ff_dir        = parse_vp_float(ambient_row['far_field_curr_dir'])

  if ambient_timeseries_files['far_field_diff_coeff'] == None:
    if not ( ambient_row['far_field_diff_coeff'] == None or ambient_row['far_field_diff_coeff'] == ''):
      ambient_data.ff_diff_coeff = parse_vp_float(ambient_row['far_field_diff_coeff'])

  if debug:
    print("Ambient Data (ambient_data):")
    print(f"ambient_data.z            : {ambient_data.z            }")
    print(f"ambient_data.current_speed: {ambient_data.current_speed}")
    print(f"ambient_data.current_dir  : {ambient_data.current_dir  }")
    print(f"ambient_data.salinity     : {ambient_data.salinity     }")
    print(f"ambient_data.temperature  : {ambient_data.temperature  }")
    print(f"ambient_data.bg_conc      : {ambient_data.bg_conc      }")
    print(f"ambient_data.decay_rate   : {ambient_data.decay_rate   }")
    print(f"ambient_data.ff_velocity  : {ambient_data.ff_velocity  }")
    print(f"ambient_data.ff_dir       : {ambient_data.ff_dir       }")
    print(f"ambient_data.ff_diff_coeff: {ambient_data.ff_diff_coeff}")

  return ambient_data

def load_timeseries_data(data):
  """
    Initiate Time Series data handler and populate with diffuser data for presenting to model analysis.
  """
  timeseries_data = model_um3.timeseries.TimeseriesHandler.TimeseriesHandler()

  timeseries_data.start_time           = parse_vp_float(data['diffuserData'][0]['start_time'])
  timeseries_data.end_time             = parse_vp_float(data['diffuserData'][0]['end_time'])
  timeseries_data.time_increment       = parse_vp_float(data['diffuserData'][0]['time_increment'])
  timeseries_data.units.start_time     = get_unit(data['diffuserStore']['start_time']['value'])
  timeseries_data.units.end_time       = get_unit(data['diffuserStore']['end_time']['value'])
  timeseries_data.units.time_increment = get_unit(data['diffuserStore']['time_increment']['value'])

  return timeseries_data

def load_ts_ambient_data(ambient_timeseries_files, ambient_store, timeseries, data):
  """
    Load Time Series Ambient file data.
  """
  if ambient_timeseries_files['current_direction'] != None:
    ts_data = data['ambientFiles']['current_direction']
    ambient_store.current_dir.z_is_depth     = ts_data['depth_or_height'] == "depth"                 # timeseries may be depth/height layers indepedently
    ambient_store.current_dir.ts_depth_units = get_unit(ts_data['depth_or_height_units'])  # depth units
    ambient_store.current_dir.units          = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    ambient_store.current_dir.ts_increment   = parse_vp_int(ts_data['increment']) 
    timeseries.ambient.current_dir           = model_um3.timeseries.AmbientTimeseries.AmbientTimeseries(ambient_timeseries_files['current_direction'], ambient_store.current_dir)
  
  if ambient_timeseries_files['current_speed'] != None:
    ts_data = data['ambientFiles']['current_speed']
    ambient_store.current_speed.z_is_depth     = ts_data['depth_or_height'] == "depth"                 # timeseries may be depth/height layers indepedently
    ambient_store.current_speed.ts_depth_units = get_unit(ts_data['depth_or_height_units'])  # depth units
    ambient_store.current_speed.units          = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    ambient_store.current_speed.ts_increment   = parse_vp_int(ts_data['increment']) 
    timeseries.ambient.current_speed           = model_um3.timeseries.AmbientTimeseries.AmbientTimeseries(ambient_timeseries_files['current_speed'], ambient_store.current_speed)

  if ambient_timeseries_files['ambient_salinity'] != None:
    ts_data = data['ambientFiles']['ambient_salinity']
    ambient_store.salinity.z_is_depth         = ts_data['depth_or_height'] == "depth"                 # timeseries may be depth/height layers indepedently
    ambient_store.salinity.ts_depth_units     = get_unit(ts_data['depth_or_height_units'])  # depth units
    ambient_store.salinity.units              = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    ambient_store.salinity.ts_increment       = parse_vp_int(ts_data['increment']) 
    timeseries.ambient.salinity = model_um3.timeseries.AmbientTimeseries.AmbientTimeseries(ambient_timeseries_files['ambient_salinity'], ambient_store.salinity)

  if ambient_timeseries_files['ambient_temperature'] != None:
    ts_data = data['ambientFiles']['ambient_temperature']
    ambient_store.temperature.z_is_depth         = ts_data['depth_or_height'] == "depth"                 # timeseries may be depth/height layers indepedently
    ambient_store.temperature.ts_depth_units     = get_unit(ts_data['depth_or_height_units'])  # depth units
    ambient_store.temperature.units              = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    ambient_store.temperature.ts_increment       = parse_vp_int(ts_data['increment']) 
    timeseries.ambient.temperature = model_um3.timeseries.AmbientTimeseries.AmbientTimeseries(ambient_timeseries_files['ambient_temperature'], ambient_store.temperature)

  if ambient_timeseries_files['background_concentration'] != None:
    ts_data = data['ambientFiles']['background_concentration']
    ambient_store.bg_conc.z_is_depth         = ts_data['depth_or_height'] == "depth"                 # timeseries may be depth/height layers indepedently
    ambient_store.bg_conc.ts_depth_units     = get_unit(ts_data['depth_or_height_units'])  # depth units
    ambient_store.bg_conc.units              = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    ambient_store.bg_conc.ts_increment       = parse_vp_int(ts_data['increment']) 
    timeseries.ambient.bg_conc = model_um3.timeseries.AmbientTimeseries.AmbientTimeseries(ambient_timeseries_files['background_concentration'], ambient_store.bg_conc)

  if ambient_timeseries_files['pollution_decay_rate'] != None:
    ts_data = data['ambientFiles']['pollution_decay_rate']
    ambient_store.decay_rate.z_is_depth         = ts_data['depth_or_height'] == "depth"                 # timeseries may be depth/height layers indepedently
    ambient_store.decay_rate.ts_depth_units     = get_unit(ts_data['depth_or_height_units'])  # depth units
    ambient_store.decay_rate.units              = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    ambient_store.decay_rate.ts_increment       = parse_vp_int(ts_data['increment']) 
    timeseries.ambient.decay_rate = model_um3.timeseries.AmbientTimeseries.AmbientTimeseries(ambient_timeseries_files['pollution_decay_rate'], ambient_store.decay_rate)

  if ambient_timeseries_files['far_field_curr_speed'] != None:
    ts_data = data['ambientFiles']['far_field_curr_speed']
    ambient_store.ff_velocity.z_is_depth         = ts_data['depth_or_height'] == "depth"                 # timeseries may be depth/height layers indepedently
    ambient_store.ff_velocity.ts_depth_units     = get_unit(ts_data['depth_or_height_units'])  # depth units
    ambient_store.ff_velocity.units              = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    ambient_store.ff_velocity.ts_increment       = parse_vp_int(ts_data['increment']) 
    timeseries.ambient.ff_velocity = model_um3.timeseries.AmbientTimeseries.AmbientTimeseries(ambient_timeseries_files['far_field_curr_speed'], ambient_store.ff_velocity)

  if ambient_timeseries_files['far_field_curr_dir'] != None:
    ts_data = data['ambientFiles']['far_field_curr_dir']
    ambient_store.ff_dir.z_is_depth         = ts_data['depth_or_height'] == "depth"                 # timeseries may be depth/height layers indepedently
    ambient_store.ff_dir.ts_depth_units     = get_unit(ts_data['depth_or_height_units'])  # depth units
    ambient_store.ff_dir.units              = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    ambient_store.ff_dir.ts_increment       = parse_vp_int(ts_data['increment']) 
    timeseries.ambient.ff_dir = model_um3.timeseries.AmbientTimeseries.AmbientTimeseries(ambient_timeseries_files['far_field_curr_dir'], ambient_store.ff_dir)

  if ambient_timeseries_files['far_field_diff_coeff'] != None:
    ts_data = data['ambientFiles']['far_field_diff_coeff']
    ambient_store.ff_diff_coeff.z_is_depth         = ts_data['depth_or_height'] == "depth"                 # timeseries may be depth/height layers indepedently
    ambient_store.ff_diff_coeff.ts_depth_units     = get_unit(ts_data['depth_or_height_units'])  # depth units
    ambient_store.ff_diff_coeff.units              = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    ambient_store.ff_diff_coeff.ts_increment       = parse_vp_int(ts_data['increment']) 
    timeseries.ambient.ff_diff_coeff = model_um3.timeseries.AmbientTimeseries.AmbientTimeseries(ambient_timeseries_files['far_field_diff_coeff'], ambient_store.ff_diff_coeff)

  return (ambient_store, timeseries)

def load_ts_diffuser_data(diff_timeseries_files, diffuser_store, timeseries, data):
  """
    Load Time Series Diffuser data
  """
  if diff_timeseries_files['port_depth'] != None:
    ts_data = data['diffuserTimeSeries']['port_depth']
    # diffuser_params.effluent_flow             = 0.001 # Can't be 0
    diffuser_store.depth.units        = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    diffuser_store.depth.ts_increment = parse_vp_int(ts_data['increment'])
    timeseries.diffuser.depth         = model_um3.timeseries.DiffuserTimeseries.DiffuserTimeseries(diff_timeseries_files['port_depth'], diffuser_store.depth)

  if diff_timeseries_files['effluent_flow'] != None:
    ts_data = data['diffuserTimeSeries']['effluent_flow']
    # diffuser_params.effluent_flow             = 0.001 # Can't be 0
    diffuser_store.effluent_flow.units        = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
    diffuser_store.effluent_flow.ts_increment = parse_vp_int(ts_data['increment'])
    timeseries.diffuser.effluent_flow         = model_um3.timeseries.DiffuserTimeseries.DiffuserTimeseries(diff_timeseries_files['effluent_flow'], diffuser_store.effluent_flow)

  if diff_timeseries_files['effluent_salinity'] != None:
      ts_data = data['diffuserTimeSeries']['effluent_salinity']
      # diffuser_params.effluent_flow             = 0.001 # Can't be 0
      diffuser_store.salinity.units        = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
      diffuser_store.salinity.ts_increment = parse_vp_int(ts_data['increment'])
      timeseries.diffuser.salinity         = model_um3.timeseries.DiffuserTimeseries.DiffuserTimeseries(diff_timeseries_files['effluent_salinity'], diffuser_store.salinity)

  if diff_timeseries_files['effluent_temp'] != None:
      ts_data = data['diffuserTimeSeries']['effluent_temp']
      # diffuser_params.effluent_flow             = 0.001 # Can't be 0
      diffuser_store.temperature.units        = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
      diffuser_store.temperature.ts_increment = parse_vp_int(ts_data['increment'])
      timeseries.diffuser.temperature         = model_um3.timeseries.DiffuserTimeseries.DiffuserTimeseries(diff_timeseries_files['effluent_temp'], diffuser_store.temperature)

  if diff_timeseries_files['effluent_concentration'] != None:
      ts_data = data['diffuserTimeSeries']['effluent_concentration']
      # diffuser_params.effluent_flow             = 0.001 # Can't be 0
      diffuser_store.concentration.units        = get_unit(ts_data['measurement_unit'])  # uses same store value, but units for value
      diffuser_store.concentration.ts_increment = parse_vp_int(ts_data['increment'])
      timeseries.diffuser.concentration         = model_um3.timeseries.DiffuserTimeseries.DiffuserTimeseries(diff_timeseries_files['effluent_concentration'], diffuser_store.concentration)

  # print("Timeseries.diffuser.effluent_flow._lines:")
  # print(timeseries.diffuser.effluent_flow._lines)
  return (diffuser_store, timeseries)

def get_temp_file_path(file):
  """
    Read file data from memory and save to temporary files. Used to feed time series files
    into file analysis.
  """
  dt = datetime.now()
  ts = datetime.timestamp(dt)
  path = default_storage.save(os.path.join(TMP_FILE_PATH,f'temp_{ts}.csv'), ContentFile(file.read()))
  tmp_file = os.path.join(settings.MEDIA_ROOT, path)
  return tmp_file

@csrf_exempt
def run_analysis(request):
  """
    Primary handler for running model analysis.
  """
  print('Analysis request recieved.')

  debug = False

  # Process Run Analysis Request
  if request.method == 'POST':

    # Obtain run analysis data
    data = json.loads(request.POST['projectData'])
    files = request.FILES

    # Get model parameters
    try:
      model_params = load_model_params(data)
    except:
      if debug:
         traceback.print_exc() 
      json_response = {
        "success":False,
        "error":"Error loading model parameter input, please check Model Selection settings."
      }
      return JsonResponse(json_response, status=200, safe=False)
       

    # Establish timeseries variable, set to None for now
    timeseries = None

    # Handle Diffuser Timeseries data
    diff_timeseries_files = {
       'port_depth': None,
       'effluent_flow': None,
       'effluent_salinity': None,
       'effluent_temp': None,
       'effluent_concentration': None
    }
    try:
      if len(files) > 0:
        timeseries = load_timeseries_data(data)
        diff_files = list(filter(lambda file: (file.split('-')[1] == 'diffuser'), files))
        for file in diff_files:
          field = file.split('-')[0]
          diff_timeseries_files[field] = get_temp_file_path(request.FILES[file])
    except:
      json_response = {
        "success":False,
        "error":"Error processing diffuser time series files, please check timeseries file format(s)."
      }
      return JsonResponse(json_response, status=200, safe=False)

    # Get diffuser store
    try:
      diffuser_store = load_diffuser_store(data)
    except:
      json_response = {
        "success":False,
        "error":"Error loading diffuser store options, please check options."
      }
      return JsonResponse(json_response, status=200, safe=False)

    # Get diffuser data
    try:
      diffuser_params = load_diffuser_params(data['diffuserData'][0], diff_timeseries_files)
    except:
      json_response = {
        "success":False,
        "error":"Error loading diffuser parameter input, please check input and re-run analysis."
      }
      return JsonResponse(json_response, status=200, safe=False)
    
    # Populate timeseries
    try:
      (diffuser_store, timeseries) = load_ts_diffuser_data(diff_timeseries_files, diffuser_store, timeseries, data)
    except:
      json_response = {
        "success":False,
        "error":"Error loading diffuser time series data, please check time series file data."
      }
      return JsonResponse(json_response, status=200, safe=False)

    # Get ambient store
    ambient_store = load_ambient_store(data['ambientProfileData'][0]['store'])

    # Handle Ambient Timeseries data
    ambient_timeseries_files = {
       'current_speed': None,
       'current_direction': None,
       'ambient_salinity': None,
       'ambient_temperature': None,
       'background_concentration': None,
       'pollution_decay_rate': None,
       'far_field_curr_speed': None,
       'far_field_curr_dir': None,
       'far_field_diff_coeff': None,
    }
    try:
      if len(files) > 0:
        ambient_files = list(filter(lambda file: (file.split('-')[1] == 'ambient'), files))
        for file in ambient_files:
          field = file.split('-')[0]
          ambient_timeseries_files[field] = get_temp_file_path(request.FILES[file])
    except:
      json_response = {
        "success":False,
        "error":"Error processing ambient time series file(s), please check ambient time series file formatting."
      }
      return JsonResponse(json_response, status=200, safe=False)

    # Get ambient data
    try:
      ambient_params_list = []
      for ambient_post_data in data['ambientProfileData'][0]['data']:
        ambient_params = load_ambient_data(ambient_post_data,ambient_timeseries_files)
        ambient_params_list.append(ambient_params)
      ambient_stack = list2tuple(ambient_params_list)
    except:
      json_response = {
        "success":False,
        "error":"Error loading ambient condition input options and/or data, please check ambient condition tabs."
      }
      return JsonResponse(json_response, status=200, safe=False)

    # Populate timeseries
    try:
      (ambient_store, timeseries) = load_ts_ambient_data(ambient_timeseries_files, ambient_store, timeseries, data)
    except:
      json_response = {
        "success":False,
        "error":"Error loading ambient time series data, please check ambient time series file data."
      }
      return JsonResponse(json_response, status=200, safe=False)

    # print(f"diff_store.effluent_flow.units: {diffuser_store.effluent_flow.units}")
    # print(f"ambient_store.current_dir.units: {ambient_store.current_dir.units}")
    # print(f"ambient_store.current_speed.units: {ambient_store.current_speed.units}")

    # Setup outputs handler
    # This may not be supplied to UMUnit, in which case default parameters will be tracked. But this is how you can
    # explicitly track variables of interest, specifying the units you want the outputs in. The order that parameters are
    # added will be the same as the order of values in the output list. You do also need to know the `regime` and var name,
    # so the output handler knows where to grab the values from. This may have to come from a hard-coded list of allowed
    # vars to track, so I will have to provide it for UI later.
    try:
      output_handler = model_um3.OutputUM3()
      output_handler.add_parameter('element', 'depth',          'Depth',     model_um3.units.Length,        diffuser_store.depth.units)
      output_handler.add_parameter('element', 'diameter',       'Width',     model_um3.units.Length,        diffuser_store.diameter.units)
      output_handler.add_parameter('element', 'vertical_angle', 'V-angle',   model_um3.units.Angle,         diffuser_store.vertical_angle.units)
      output_handler.add_parameter('element', 'salinity',       'Salinity',  model_um3.units.Salinity,      ambient_store.salinity.units)
      output_handler.add_parameter('element', 'temperature',    'Temp.',     model_um3.units.Temperature,   ambient_store.temperature.units)
      output_handler.add_parameter('element', 'concentration',  'Pollutant', model_um3.units.Concentration, diffuser_store.concentration.units)
      output_handler.add_parameter('element', 'density',        'Density',   model_um3.units.Density,       model_um3.units.Density.SIGMA_T)
      output_handler.add_parameter('ambient', 'density',        'Amb-den',   model_um3.units.Density,       model_um3.units.Density.SIGMA_T)
      output_handler.add_parameter('ambient', 'current_speed',  'Amb-cur',   model_um3.units.Speed,         ambient_store.current_speed.units)
      output_handler.add_parameter('element', 'speed',          'Velocity',  model_um3.units.Speed,         model_um3.units.Speed.METERS_PER_SECOND)
      output_handler.add_parameter('element', 'dilution',       'Dilution',  model_um3.units.Unitless,      model_um3.units.Unitless.UNITLESS)
      output_handler.add_parameter('element', 'x_displacement', 'X-pos',     model_um3.units.Length,        model_um3.units.Length.FEET)
      output_handler.add_parameter('element', 'y_displacement', 'Y-pos',     model_um3.units.Length,        model_um3.units.Length.FEET)
      # output_handler.add_parameter('element', 'mass',           'Mass',      units.Mass,          units.Mass.KILOGRAMS)
      # output_handler.add_parameter('element', 'd_mass',         'Entrained', units.Mass,          units.Mass.KILOGRAMS)
      output_handler.add_parameter('model',    'iso_diameter',  'Iso diameter', model_um3.units.Length,     diffuser_store.diameter.units)
    except:
      json_response = {
        "success":False,
        "error":"Error initializing UM3 model, please contact site administrators."
      }
      return JsonResponse(json_response, status=200, safe=False)
    
    # Start Model Analysis
    try:
      output_dict = model_um3.Middleware.run(
        model_params       = model_params,
        diffuser_params    = diffuser_params,
        diffuser_store     = diffuser_store,
        timeseries_handler = timeseries,
        ambient_stack      = ambient_stack,
        ambient_store      = ambient_store,
        output_handler     = output_handler
      )
    except Exception as e:
      print("Error running model analysis:")
      print(e)
      json_response = {
        "success":False,
        "error":str(e)
      }
      return JsonResponse(json_response, status=200, safe=False)
      

    # Generate text output, to be sent to UI for display in Text Output area
    if output_dict and output_dict["success"]:
      temp_out = StringIO()
      sys.stdout = temp_out
      print_outputs(output_dict)
      sys.stdout = sys.__stdout__
      output_dict['text_outputs'] = temp_out.getvalue()
    elif output_dict["error"]:
        print(output_dict["error"])
        json_response = {
          "success":False,
          "error":str(output_dict["error"])
        }
        return JsonResponse(json_response, status=200, safe=False)
    else:
        print("Unknown error running model analysis")


    # Write CSV files
    # Expect: 
    #   - output_{ts}.params.txt
    #   - output_{ts}.diffuser.csv
    #   - output_{ts}.ambient.csv
    #   - output_{ts}.memos.txt
    #   - output_{ts}.plume.csv
    #   - output_{ts}.farfield.csv
    #   - output_{ts}.tpb.txt
    dt = datetime.now()
    ts = datetime.timestamp(dt) # model_run_id
    try:
      
      # Generate CSV output
      csv_outputs(output_dict,TMP_FILE_PATH,f'output_{ts}.csv')

      # Gather list of output files
      csv_output_files = glob.glob(os.path.join(TMP_FILE_PATH,f'output_{ts}.*'))

      # Ensure we have more than 1 file
      if len(csv_output_files) < 1:
        raise Exception
      
      # Create zip archive
      output_archive_file_name = os.path.join(TMP_FILE_PATH,f'output_{ts}.zip')
      with zipfile.ZipFile(output_archive_file_name, 'w') as output_archive:        
        for file in csv_output_files:
            output_archive.write(file, os.path.basename(file), compress_type=zipfile.ZIP_DEFLATED)

      # Delete archive files, keep zip file only
      if os.path.exists(output_archive_file_name):
        for file in csv_output_files:
          os.remove(file)
      
      # Include output id
      output_dict['output_id'] = ts
    
    except:
      json_response = {
        "success":False,
        "error":"Visual Plumes failed to write CSV files."
      }
      return JsonResponse(json_response, status=200, safe=False)

    # Convert python types into their qualified names, necessary for converting to JSON
    def default_json(obj):
       return obj.__qualname__

    # Transform output data structure into JSON
    try:
      json_response = json.dumps(output_dict, default=default_json)
    except:
      print(e)
      json_response = {
        "success":False,
        "error":str(e)
      }
      return JsonResponse(json_response, status=200, safe=False)

  # Print success if not a POST request, helpufl for determining if Django is running properly.
  else:
    json_response = {
      "message":"Success!"
    }

  return JsonResponse(json_response, status=200, safe=False)

def print_outputs(output_dict):
    """
      Generate output text, returned to UI and displayed in text output section.
    """
    # prep diffuser output formatting (since same for all cases)
    diff_outs = output_dict['diffuser']
    header_vals = []
    units_vals = []
    format_header = []
    format_output = []
    for i, hdr in enumerate(diff_outs['headers']):
        header_vals.append(hdr['label'])
        hdr_len = len(hdr['label']) + (1 if i > 0 else 0)
        hdr_units = hdr['units']
        format_header.append("{" + str(i) + ":>" + str(hdr_len) + "}")
        if i == 0 or hdr_units == model_um3.units.FlowRate:
            format_output.append("{" + str(i) + ":" + str(hdr_len) + ".5f}")
        else:
            format_output.append("{" + str(i) + ":" + str(hdr_len) + ".1f}")
        if hdr['units_label'] == "":
            units_vals.append("")
        else:
            units_vals.append(f"({hdr['units_label']})")
    diff_format_header = " ".join(format_header)
    diff_format_output = " ".join(format_output)
    diff_str_header = diff_format_header.format(*header_vals)
    diff_str_units = diff_format_header.format(*units_vals)

    # prep ambient output formatting (since same for all cases)
    ambient_outs = output_dict['ambient']
    header_vals = []
    units_vals = []
    format_header = []
    format_output = []
    for i, hdr in enumerate(ambient_outs['headers']):
        header_vals.append(hdr['label'])
        hdr_len = len(hdr['label']) + (1 if i > 0 else 0)
        if hdr_len < 7:
            hdr_len = 7
        if hdr['units_label'] == "":
            units_vals.append("")
        else:
            units_vals.append(f"({hdr['units_label']})")
        if hdr['label'].startswith("Far-field"):
            continue
        if hdr['units'] == model_um3.units.Angle:
            val_precision = 0
        elif hdr['units'] == model_um3.units.Length:
            val_precision = 3
        elif hdr['units'] in (model_um3.units.Speed, model_um3.units.Density, model_um3.units.DecayRate):
            val_precision = 4
        elif hdr['units'] in (model_um3.units.Concentration, model_um3.units.Salinity, model_um3.units.Temperature):
            val_precision = 2
        else:
            val_precision = 1
        format_header.append("{" + str(i) + ":>" + str(hdr_len) + "}")
        format_output.append("{" + str(i) + ":" + str(hdr_len) + "." + str(val_precision) + "f}")
    amb_format_header = " ".join(format_header)
    amb_format_output = " ".join(format_output)
    amb_str_header = amb_format_header.format(*header_vals)
    amb_str_units = amb_format_header.format(*units_vals)

    # prep model output formatting (since same for all cases)
    model_outs = output_dict['plume']
    format_header = ["{0:>5}"]
    format_output = ["{0:5}"]
    header_vals = ["Step"]
    units_vals = [""]
    # output_handler.headers() returns a generation/yield, so if you want to package it, wrap it in a list() or tuple()
    for i, hdr in enumerate(model_outs['headers']):
        header_vals.append(hdr['label'])
        if hdr['units_label'] == "":
            units_vals.append("")
        else:
            units_vals.append("(" + hdr['units_label'] + ")")
        # if hdr['units'] == units.DecayRate:
        #     format_header.append("{" + str(i + 1) + ":>10}")
        #     format_output.append("{" + str(i + 1) + ":10.1f}")
        if hdr['units'] == model_um3.units.Angle:
            format_header.append("{" + str(i + 1) + ":>8}")
            format_output.append("{" + str(i + 1) + ":8.3f}")
        elif hdr['name'] == 'd_mass':
            format_header.append("{" + str(i + 1) + ":>9}")
            format_output.append("{" + str(i + 1) + ":9.5f}")
        elif hdr['units'] == model_um3.units.Density:
            format_header.append("{" + str(i + 1) + ":>9}")
            format_output.append("{" + str(i + 1) + ":9.4f}")
        elif hdr['units'] in (model_um3.units.Concentration, model_um3.units.Speed):
            format_header.append("{" + str(i + 1) + ":>9}")
            format_output.append("{" + str(i + 1) + ":9.3f}")
        elif hdr['name'] == 'dilution':
            format_header.append("{" + str(i + 1) + ":>9}")
            format_output.append("{" + str(i + 1) + ":9,.3f}")
        elif hdr['name'] == 'diameter' or hdr['units'] == model_um3.units.DecayRate:
            format_header.append("{" + str(i + 1) + ":>9}")
            format_output.append("{" + str(i + 1) + ":9,.4f}")
        elif hdr['name'] in ('depth', 'iso_diameter', 'x_displacement', 'y_displacement'):
            format_header.append("{" + str(i + 1) + ":>9}")
            format_output.append("{" + str(i + 1) + ":9,.3f}")
        else:
            format_header.append("{" + str(i + 1) + ":>9}")
            format_output.append("{" + str(i + 1) + ":9.2f}")
    model_format_header = " ".join(format_header)
    model_format_output = " ".join(format_output)
    model_str_header = model_format_header.format(*header_vals)
    model_str_units = model_format_header.format(*units_vals)

    # prep brooks far-field model formatting (since same for all cases)
    ff_outs = output_dict['farfield']
    format_header = []
    format_output = []
    header_vals = []
    units_vals = []
    if ff_outs['was_run'] and len(ff_outs['headers']):
        for i, hdr in enumerate(ff_outs['headers']):
            header_vals.append(hdr['label'])
            if hdr['units_label'] == "":
                units_vals.append("")
            else:
                units_vals.append(f"({hdr['units_label']})")
            hdr_len = len(hdr['label']) + (1 if i > 0 else 0)
            if hdr_len < 6:
                hdr_len = 6
            val_precision = 1
            match hdr['name']:
                case 'dilution':
                    val_precision = 1
                    if hdr_len < 9:
                        hdr_len = 9
                case 'adj_width':
                    val_precision = 0
                    if hdr_len < 8:
                        hdr_len = 8
                case 'total_surf_dsp':
                    val_precision = 1
                    if hdr_len < 9:
                        hdr_len = 9
                case 'ff_diff_coeff':
                    val_precision = 4
                    if hdr_len < 12:
                        hdr_len = 12
                case 'diffusivity':
                    val_precision = 4
                    if hdr_len < 9:
                        hdr_len = 9
                case _:
                    if hdr['units'] in (model_um3.units.Speed, model_um3.units.Time):
                        val_precision = 2
                        if hdr_len < 8:
                            hdr_len = 8
                    elif hdr['units'] == model_um3.units.Concentration:
                        val_precision = 4
            format_header.append("{" + str(i) + ":>" + str(hdr_len) + "}")
            format_output.append("{" + str(i) + ":" + str(hdr_len) + ",." + str(val_precision) + "f}")
        ff_format_header = " ".join(format_header)
        ff_format_output = " ".join(format_output)
        ff_str_header = ff_format_header.format(*header_vals)
        ff_str_units = ff_format_header.format(*units_vals)
    else:
        ff_format_header = ""
        ff_format_output = ""
        ff_str_header = ""
        ff_str_units = ""

    # print model parameters header
    if 'modelparams' in output_dict:
        for memo in output_dict['modelparams']['memos']:
            print(memo)
        print("")

    # loop outputs by case run
    for case_i in range(output_dict['cases']):
        print("\n---------------------------------------------------")
        print(f"Case {1 + case_i} (+{output_dict['casetime'][case_i]/3600.0:.2f} hrs):")
        print("---------------------------------------------------")

        # print timeseries indices
        if output_dict['timeseries']:
            for memo in output_dict['timeseries']['memos'][case_i]:
                print(memo)

        # print diffuser params
        print("")
        print(diff_str_header)
        print(diff_str_units)
        print(diff_format_output.format(*diff_outs['outputs'][case_i]))

        # print ambient params
        print("")
        print(amb_str_header)
        print(amb_str_units)
        for amb_level in ambient_outs['outputs'][case_i]:
            print(amb_format_output.format(*amb_level))

        # print memos
        memos = model_outs['memos'][case_i]
        if len(memos):
            print("\n" + "\n".join(memos))

        # print output table
        print("")
        print(model_str_header)
        print(model_str_units)
        for output in model_outs['outputs'][case_i]:
            print(model_format_output.format(*([output['step']] + output['values'])) + f";  {output['status']}")

        # print post memos
        memos = model_outs['postmemos'][case_i]
        if len(memos):
            print("\n" + "\n".join(memos))

        # print ff output table
        if ff_outs['was_run']:
            print("")
            for memo in ff_outs['memos'][case_i]:
                print(memo)
            print("")
            if ff_str_header:
                print(ff_str_header)
                print(ff_str_units)
            for output in ff_outs['outputs'][case_i]:
                if len(output):
                    print(ff_format_output.format(*output['values']))

    # print ff output table
    if output_dict['tpb']['was_run']:
        print("")
        print("---------------------------------------------------")
        print("")
        for memo in output_dict['tpb']['memos']:
            print(memo)

def csv_outputs(output_dict, folderpath, filename_format):
    case_digits = int(math.log10(output_dict['cases']))
    if case_digits < 2:
        case_digits = 2
    case_format = "{0:0" + str(case_digits) + "d}"
    if filename_format.lower().endswith(".csv"):
        filename_format = filename_format[:-4]

    if not os.path.exists(folderpath):
        os.makedirs(folderpath)

    # print general params
    fp_memos = os.path.join(folderpath, f"{filename_format}.params.txt")
    with open(fp_memos, 'w', encoding='utf-8') as fmemo:
        # print model param memos
        memos = output_dict['modelparams']['memos']
        if len(memos):
            fmemo.write("\n".join(memos) + "\n")

    diff_outs = output_dict['diffuser']
    amb_outs  = output_dict['ambient']
    um_outs   = output_dict['plume']
    ff_outs   = output_dict['farfield']
    tpb_outs  = output_dict['tpb']

    # prep headers for diffuser outputs
    diff_header_vals = ["Case"]
    for i, hdr in enumerate(diff_outs['headers']):
        header_text = hdr['label']
        if hdr['units_label'] != "":
            header_text += f" ({hdr['units_label']})"
        diff_header_vals.append(header_text)
    # prep headers for ambient outputs
    amb_header_vals = []
    for i, hdr in enumerate(amb_outs['headers']):
        header_text = hdr['label']
        if hdr['units_label'] != "":
            header_text += f" ({hdr['units_label']})"
        amb_header_vals.append(header_text)
    # prep headers for plume outputs
    header_vals = ["Step"]
    for i, hdr in enumerate(um_outs['headers']):
        header_text = hdr['label']
        if hdr['units_label'] != "":
            header_text += f" ({hdr['units_label']})"
        header_vals.append(header_text)
    # prep headers for brooks ff outputs
    ff_header_vals = []
    if ff_outs['was_run'] and len(ff_outs['headers']):
        for i, hdr in enumerate(ff_outs['headers']):
            header_text = hdr['label']
            if hdr['units_label'] != "":
                header_text += f" ({hdr['units_label']})"
            ff_header_vals.append(header_text)

    # diffuser csv
    fp_diff = os.path.join(folderpath, f"{filename_format}.diffuser.csv")
    with open(fp_diff, 'w', newline='', encoding='utf-8') as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow(diff_header_vals)
        for case_i, outputs in enumerate(diff_outs['outputs']):
            writer.writerow([case_i+1] + list(outputs))

    # loop by case
    for case_i in range(output_dict['cases']):
        case_n  = case_i+1
        case_fn = case_format.format(case_n)

        # ambient csv
        fp_amb = os.path.join(folderpath, f"{filename_format}.{case_fn}.ambient.csv")
        with open(fp_amb, 'w', newline='', encoding='utf-8') as fcsv:
            writer = csv.writer(fcsv)
            writer.writerow(amb_header_vals)
            writer.writerows(amb_outs['outputs'][case_i])

        # print memos
        fp_memos = os.path.join(folderpath, f"{filename_format}.{case_fn}.memos.txt")
        with open(fp_memos, 'w', encoding='utf-8') as fmemo:
            fmemo.write("---------------------------------------------------\n")
            fmemo.write(f"Case {case_n} (+{output_dict['casetime'][case_i]/3600.0:.2f} hrs):\n")
            fmemo.write("---------------------------------------------------\n")
            # print timeseries indices
            if output_dict['timeseries']:
                for memo in output_dict['timeseries']['memos'][case_i]:
                    fmemo.write(memo+"\n")
            # print model memos
            memos = um_outs['memos'][case_i]
            if len(memos):
                fmemo.write("\n" + "\n".join(memos) + "\n")
            # print post model memos
            memos = um_outs['postmemos'][case_i]
            if len(memos):
                fmemo.write("\n" + "\n".join(memos) + "\n")
            # print ff memos
            if ff_outs['was_run']:
                fmemo.write("\n" + "\n".join(ff_outs['memos'][case_i]) + "\n")

        # plume csv
        fp_plume = os.path.join(folderpath, f"{filename_format}.{case_fn}.plume.csv")
        with open(fp_plume, 'w', newline='', encoding='utf-8') as fcsv:
            writer = csv.writer(fcsv)
            writer.writerow(header_vals)
            for output in um_outs['outputs'][case_i]:
                writer.writerow([output['step']] + output['values'] + [output['status']])

        # brooks ff csv
        if ff_outs['was_run']:
            fp_bff = os.path.join(folderpath, f"{filename_format}.{case_fn}.farfield.csv")
            with open(fp_bff, 'w', newline='', encoding='utf-8') as fcsv:
                writer = csv.writer(fcsv)
                writer.writerow(ff_header_vals)
                for output in ff_outs['outputs'][case_i]:
                    writer.writerow(output['values'])

    # tidal pollution buildup outputs
    if tpb_outs['was_run']:
        fp_tpb = os.path.join(folderpath, f"{filename_format}.tpb.txt")
        with open(fp_tpb, 'w', newline='', encoding='utf-8') as ftxt:
            ftxt.write("\n".join(tpb_outs['memos']))

def download_zip_archive(request,model_run_id):
  """ 
    Returns archive zip file containing model analysis output.
  """
  zip_archive_path = os.path.join(TMP_FILE_PATH,f'output_{model_run_id}.zip')
  response = FileResponse(open(zip_archive_path, "rb"))
  return response