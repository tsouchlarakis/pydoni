import pydoni
import pydoni.vb


class EXIF(object):
    """
    Extract and operate on EXIF metadata from a media file or multiple files. Wrapper for
    `exiftool` by Phil Harvey system command.

    :param fname: full path to target filename or list of filenames
    :type fname: str, list
    """

    def __init__(self, fpath):
        import os
        import subprocess
        import pydoni
        import pydoni.sh

        self.fpath = pydoni.ensurelist(fpath)
        self.fpath = [os.path.abspath(f) for f in self.fpath]
        for f in self.fpath:
            assert os.path.isfile(f)

        self.is_batch = len(self.fpath) > 1
        self.bin = pydoni.sh.find_binary('exiftool')

        assert os.path.isfile(self.bin)

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.logger.var('self.fpath', self.fpath)
        self.logger.var('self.is_batch', self.is_batch)
        self.logger.var('self.bin', self.bin)

        self.logger.info('EXIF class initialized for file{}: {}'.format(
            's' if self.is_batch else '', str(self.fpath)))

    def extract(self, method='doni', clean=True):
        """
        Extract EXIF metadata from file or files.

        :param method: method for metadata extraction, one of 'doni' or 'pyexiftool'
        :type method: str
        :param clean: apply EXIF.clean() to EXIF output
        :type clean: bool
        :return: EXIF metadata
        :rtype: dict
        """
        import re
        import os
        from xml.etree import ElementTree
        from collections import defaultdict
        import subprocess

        assert method in ['doni', 'pyexiftool']

        self.logger.var('self.method', method)
        self.logger.var('self.clean', clean)

        def split_cl_filenames(files, char_limit, bin_path):
            """
            Determine at which point to split list of filenames to comply with command-line
            character limit, and split list of filenames into list of lists, where each sublist
            represents a batch of files to run `exiftool` on, where the entire call to `exiftool`
            for that batch will be under the maximum command-line character limit. Files must
            be broken into batches if there are too many to fit on in command-line command,
            because the `exiftool` syntax is as follows:

            exiftool filename_1 filename_2 filename_3 ... filename_n

            With too many files, the raw length of the call to `exiftool` might be over the
            character limit.

            :param files: path to file or files to run exiftool on
            :type files: list
            :param char_limit: character limit of operating system's command-line character limit
            :type char_limit: int
            :param bin_path: path to exiftool binary
            :type bin_path: str
            :return: list of filenames to run exiftool on
            :rtype: list
            """

            self.logger.var('files', files)
            self.logger.var('char_limit', char_limit)
            self.logger.var('bin_path', bin_path)

            split_idx = []
            count = 0

            # Get character length of each filename
            str_lengths = [len(x) for x in files]

            # Get indices to split at depending on character limit
            for i in range(len(str_lengths)):
                # Account for two double quotes and a space
                val = str_lengths[i] + 3
                count = count + val
                if count > char_limit - len(bin_path + ' '):
                    split_idx.append(i)
                    count = 0

            # Split list of filenames into list of lists at the indices gotten in
            # the previous step
            return pydoni.split_at(files, split_idx)

        def etree_to_dict(t):
            """
            Convert XML ElementTree to dictionary.

            Source: https://stackoverflow.com/questions/7684333/converting-xml-to-dictionary-using-elementtree

            :param t: XML ElementTree
            :type t: ElementTree
            :return: dictionary
            :rtype: dict
            """

            self.logger.var('t', t)

            d = {t.tag: {} if t.attrib else None}
            children = list(t)

            if children:
                dd = defaultdict(list)
                for dc in map(etree_to_dict, children):
                    for k, v in dc.items():
                        dd[k].append(v)
                d = {t.tag: {k: v[0] if len(v) == 1 else v
                             for k, v in dd.items()}}

            if t.attrib:
                d[t.tag].update(('@' + k, v)
                                for k, v in t.attrib.items())

            if t.text:
                text = t.text.strip()
                if children or t.attrib:
                    if text:
                      d[t.tag]['#text'] = text
                else:
                    d[t.tag] = text

            return d

        def unnest_http_keynames(d):
            """
            Iterate over dictionary and test for key:value pairs where `value` is a
            dictionary with a key name in format "{http://...}". Iterate down until the
            terminal value is retrieved, then return that value to the original key name `key`

            :param d: dictionary to iterate over
            :type d: dict
            :returns: dictionary with simplified key:value pairs
            :rtype: dict
            """
            self.logger.var('d', d)

            tmpd = {}

            for k, v in d.items():

                while isinstance(v, dict) and len(v) == 1:
                    key = list(v.keys())[0]
                    if re.search(r'\{http:\/\/.*\}', key):
                        v = v[key]
                    else:
                        break

                tmpd[k] = v

            return tmpd


        self.logger.info("Running with method: " + method)

        if method == 'doni':
            num_files = len(self.fpath) if self.is_batch else 1
            self.logger.info("Extracting EXIF for files: " + str(num_files))
            self.logger.info("Exiftool binary found: " + self.bin)

            char_limit = int(pydoni.syscmd("getconf ARG_MAX")) - 25000
            self.logger.info("Using char limit: " + str(char_limit))

            file_batches = split_cl_filenames(self.fpath, char_limit, self.bin)
            self.logger.info("Batches to run: " + str(len(file_batches)))

            commands = []
            for batch in file_batches:
                cmd = self.bin + ' -xmlFormat ' + ' '.join(['"' + f + '"' for f in batch]) + ' ' + '2>/dev/null'
                commands.append(cmd)

            exifd = {}

            for i, cmd in enumerate(commands):
                self.logger.info("Running batch %s of %s. Total files: %s" % \
                    (str(i+1), str(len(file_batches)), str(len(file_batches[i]))))

                try:
                    # xmlstring = pydoni.syscmd(cmd).decode('utf-8')
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
                    xmlstring, err = proc.communicate()
                    xmlstring = xmlstring.decode('utf-8')
                except Exception as e:
                    self.logger.exception("Failed in executing `exiftool` system command")
                    raise e

                try:
                    root = ElementTree.fromstring(xmlstring)
                    elist = etree_to_dict(root)
                    elist = elist['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF']
                    elist = elist['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description']
                    if isinstance(elist, dict):
                        elist = [elist]

                except Exception as e:
                    self.logger.info("Failed in coercing ElementTree to dictionary")
                    raise e

                for d in elist:
                    tmpd = {}

                    # Clean dictionary keys in format @{http://...}KeyName
                    for k, v in d.items():
                        new_key = re.sub(r'@?\{.*\}', '', k)
                        tmpd[new_key] = v

                    # Unnest nested dictionary elements with "http://..." as the keys
                    tmpd = unnest_http_keynames(tmpd)

                    fnamekey = os.path.join(tmpd['Directory'], tmpd['FileName'])
                    exifd[fnamekey] = tmpd

                del elist

            self.logger.info("Successfully extracted EXIF metadata for named file(s)")

            if clean:
                exifd = self.clean_keys(exifd)
                exifd = self.clean_values(exifd)
                return exifd
            else:
                return exifd

        elif method == 'pyexiftool':
            import exiftool
            with exiftool.ExifTool() as et:
                if self.is_batch:
                    exifd = et.get_metadata_batch(self.fpath)
                else:
                    exifd = et.get_metadata(self.fpath)

            return exifd

    def write(self, tags, values):
        """
        Write EXIF attribute(s) on a file or list of files.

        :param tags: tag names to write to
        :type tags: str, list
        :param values: desired tag values
        :type values: str, list
        :return: True
        :rtype: bool
        """

        import pydoni
        import pydoni.sh

        self.logger.var('tags', tags)
        self.logger.var('values', values)

        tags = [tags] if isinstance(tags, str) else tags
        values = [values] if isinstance(values, str) or isinstance(values, int) else values
        assert len(tags) == len(values)

        self._is_valid_tag_name(tags)

        self.logger.info("Files to write EXIF metadata to: " + str(len(self.fpath)))
        self.logger.info("Tags to write: " + str(tags))
        self.logger.info("Values to write: " + str(values))

        for file in self.fpath:
            self.logger.info("File: " + file)

            for tag, value in zip(tags, values):

                default_cmd = '{} -overwrite_original -{}="{}" "{}"'.format(
                    self.bin, tag, str(value), file)

                if tag == 'Keywords':
                    # Must be written in format:
                    # exiftool -keywords=one -keywords=two -keywords=three FILE
                    # Otherwise, comma-separated keywords will be written as a single string
                    if isinstance(value, str):
                        if ',' in value:
                            value = value.split(', ')

                    if isinstance(value, list):
                        if len(value) > 1:
                            kwd_cmd = ' '.join(['-keywords="' + str(x) + '"' for x in value])

                    if 'kwd_cmd' in locals():
                        cmd = '{} -overwrite_original {} "{}"'.format(
                            self.bin, kwd_cmd, file)
                    else:
                        cmd = default_cmd

                else:
                    cmd = default_cmd

                try:
                    self.logger.var('cmd', cmd)
                    res = pydoni.syscmd(cmd, encoding='utf-8')
                    self.logger.var('res', res)

                    if self._is_valid_tag_message(res):
                        self.logger.info("Success. Tag: %s | Value: %s" % (tag, str(value)))
                    else:
                        self.logger.info("Failed. Tag: %s | Value: %s" % (tag, str(value)))

                except Exception as e:
                    self.logger.exception("Failed. Tag: %s | Value: %s" % (tag, str(value)))
                    raise e

        return True

    def remove(self, tags):
        """
        Remove EXIF attribute from a file or list of files.

        :param tags: tag names to remove
        :type tags: str, list
        :return: True
        :rtype: bool
        """

        self.logger.var('tags', tags)

        tags = [tags] if isinstance(tags, str) else tags

        self._is_valid_tag_name(tags)

        self.logger.info("Files to remove EXIF metadata from: " + str(len(self.fpath)))
        self.logger.info("Tags to remove: " + str(tags))

        for file in self.fpath:
            self.logger.info("File: " + file)

            for tag in tags:
                cmd = '{} -overwrite_original -{}= "{}"'.format(self.bin, tag, file)

                try:
                    self.logger.var('cmd', cmd)
                    res = pydoni.syscmd(cmd, encoding='utf-8')
                    self.logger.var('res', res)

                    if self._is_valid_tag_message(res):
                        self.logger.info("Success. Tag: %s" % tag)
                    else:
                        self.logger.error("ExifTool Error. Tag: %s" % tag)
                        self.logger.debug('ExifTool output: %s' % str(res))

                except Exception as e:
                    self.logger.exception("Failed. Tag: %s" % tag)
                    raise e

    def clean_values(self, exifd):
        """
        Attempt to coerce EXIF values to Python data structures where possible. Try to coerce
        numerical values to Python int or float datatypes, dates to Python datetime values,
        and so on.

        Examples:
            '+7' -> 7
            '-7' -> -7
            '2018:02:29 01:28:10' -> '2018-02-29 01:28:10'
            '11.11' -> 11.11

        :param exifd: dictionary of extracted EXIF metadata
        :type exifd: dict
        :return: dictionary with cleaned values where possible
        :type: dict
        """

        self.logger.var('exifd', exifd)

        def detect_dtype(val):
            """
            Detect datatype of value.

            :param val: value to test
            :type val: any
            :return: one of ['bool', 'float', 'int', 'date', 'datetime', 'str']
            :rtype: str
            """

            self.logger.var('val', val)

            for dtype in ['bool', 'float', 'int', 'datetime', 'date', 'str']:
                if dtype == 'str':
                    return dtype
                else:
                    if pydoni.test(val, dtype):
                        return dtype

            return 'str'

        newexifd = {}
        for file, d in exifd.items():
            newexifd[file] = {}

            for k, v in d.items():
                dtype = detect_dtype(v)
                if dtype in ['bool', 'date', 'datetime', 'int', 'float']:
                    coerced_value = pydoni.test(v, dtype, return_coerced_value=True)
                    if v != coerced_value:
                        newexifd[file][k] = coerced_value
                        continue

                newexifd[file][k] = v

        return newexifd

    def clean_keys(self, exifd):
        """
        Clean EXIF element names.
        """
        column_map = {
            'about': 'about',
            'About': 'about',
            'AbsoluteAltitude': 'absolute_altitude',
            'ActiveArea': 'active_area',
            'AddAspectRatioInfo': 'add_aspect_ratio_info',
            'AddIPTCInformation': 'add_iptc_information',
            'AEBAutoCancel': 'aeb_auto_cancel',
            'AEBBracketValue': 'aeb_bracket_value',
            'AEBSequence': 'aeb_sequence',
            'AEBShotCount': 'aeb_shot_count',
            'AFAccelDecelTracking': 'af_accel_decel_tracking',
            'AFAreaHeights': 'af_area_heights',
            'AFAreaMode': 'af_area_mode',
            'AFAreaModeSetting': 'af_area_mode_setting',
            'AFAreaSelectionMethod': 'af_area_selection_method',
            'AFAreaWidths': 'af_area_widths',
            'AFAreaXPositions': 'af_area_x_positions',
            'AFAreaYPositions': 'af_area_y_positions',
            'AFAssistBeam': 'af_assist_beam',
            'AFConfigTool': 'af_config_tool',
            'AFImageHeight': 'af_image_height',
            'AFImageWidth': 'af_image_width',
            'AFMicroAdjMode': 'af_micro_adj_mode',
            'AFMicroAdjValue': 'af_micro_adj_value',
            'AFPointDisplayDuringFocus': 'af_point_display_during_focus',
            'AFPointSelected': 'af_point_selected',
            'AFPointsInFocus': 'af_points_in_focus',
            'AFPointsSelected': 'af_points_selected',
            'AFPointsUsed': 'af_points_used',
            'AFPointSwitching': 'af_point_switching',
            'AFTracking': 'af_tracking',
            'AFTrackingSensitivity': 'af_tracking_sensitivity',
            'AIServoFirstImage': 'ai_servo_first_image',
            'AIServoSecondImage': 'ai_servo_second_image',
            'AlreadyApplied': 'already_applied',
            'AmbientTemperature': 'ambient_temperature',
            'AnalogBalance': 'analog_balance',
            'Anti-Blur': 'anti_blur',
            'AntiAliasStrength': 'anti_alias_strength',
            'Aperture': 'aperture',
            'ApertureRange': 'aperture_range',
            'ApertureValue': 'aperture_value',
            'ApplicationRecordVersion': 'application_record_version',
            'Artist': 'artist',
            'AspectRatio': 'aspect_ratio',
            'AsShotNeutral': 'as_shot_neutral',
            'AutoExposureBracketing': 'auto_exposure_bracketing',
            'AutoISO': 'auto_iso',
            'AutoLateralCA': 'auto_lateral_ca',
            'AutoLightingOptimizer': 'auto_lighting_optimizer',
            'AutoPortraitFramed': 'auto_portrait_framed',
            'AverageBlackLevel': 'average_black_level',
            'BaseISO': 'base_iso',
            'BaselineExposure': 'baseline_exposure',
            'BaselineNoise': 'baseline_noise',
            'BaselineSharpness': 'baseline_sharpness',
            'BatteryLevel': 'battery_level',
            'BatteryTemperature': 'battery_temperature',
            'BatteryType': 'battery_type',
            'BayerGreenSplit': 'bayer_green_split',
            'BestQualityScale': 'best_quality_scale',
            'BitDepth': 'bit_depth',
            'BitsPerSample': 'bits_per_sample',
            'BlackLevel': 'black_level',
            'BlackLevelRepeatDim': 'black_level_repeat_dim',
            'BlackMaskBottomBorder': 'black_mask_bottom_border',
            'BlackMaskLeftBorder': 'black_mask_left_border',
            'BlackMaskRightBorder': 'black_mask_right_border',
            'BlackMaskTopBorder': 'black_mask_top_border',
            'Blacks2012': 'blacks_2012',
            'BlueBalance': 'blue_balance',
            'BlueHue': 'blue_hue',
            'BlueMatrixColumn': 'blue_matrix_column',
            'BlueSaturation': 'blue_saturation',
            'BlueTRC': 'blue_trc',
            'BracketMode': 'bracket_mode',
            'BracketShotNumber': 'bracket_shot_number',
            'BracketValue': 'bracket_value',
            'Brightness': 'brightness',
            'BrightnessValue': 'brightness_value',
            'BulbDuration': 'bulb_duration',
            'By': 'by',
            'By-line': 'by_line',
            'CalibrationIlluminant1': 'calibration_illuminant_1',
            'CalibrationIlluminant2': 'calibration_illuminant_2',
            'CameraE': 'camera_e',
            'CameraE-mountVersion': 'camera_e_mount_version',
            'CameraISO': 'camera_iso',
            'CameraOrientation': 'camera_orientation',
            'CameraProfile': 'camera_profile',
            'CameraProfileDigest': 'camera_profile_digest',
            'CameraSerialNumber': 'camera_serial_number',
            'CameraTemperature': 'camera_temperature',
            'CameraType': 'camera_type',
            'CamReverse': 'cam_reverse',
            'CanonExposureMode': 'canon_exposure_mode',
            'CanonFirmwareVersion': 'canon_firmware_version',
            'CanonFlashMode': 'canon_flash_mode',
            'CanonImageHeight': 'canon_image_height',
            'CanonImageSize': 'canon_image_size',
            'CanonImageType': 'canon_image_type',
            'CanonImageWidth': 'canon_image_width',
            'CanonModelID': 'canon_model_id',
            'Caption': 'caption',
            'Caption-Abstract': 'caption_abstract',
            'CFALayout': 'cfa_layout',
            'CFAPattern': 'cfa_pattern',
            'CFAPattern2': 'cfa_pattern_2',
            'CFAPlaneColor': 'cfa_plane_color',
            'CFARepeatPatternDim': 'cfa_repeat_pattern_dim',
            'ChromaticAberrationCorrection': 'chromatic_aberration_correction',
            'ChromaticAberrationCorrParams': 'chromatic_aberration_corr_params',
            'ChromaticAberrationSetting': 'chromatic_aberration_setting',
            'CircGradBasedCorrActive': 'circ_grad_based_corr_active',
            'CircGradBasedCorrAmount': 'circ_grad_based_corr_amount',
            'CircGradBasedCorrClarity2012': 'circ_grad_based_corr_clarity_2012',
            'CircGradBasedCorrContrast2012': 'circ_grad_based_corr_contrast_2012',
            'CircGradBasedCorrCorrectionRangeMaskColorAmount': 'circ_grad_based_corr_correction_range_mask_color_amount',
            'CircGradBasedCorrCorrectionRangeMaskLumFeather': 'circ_grad_based_corr_correction_range_mask_lum_feather',
            'CircGradBasedCorrCorrectionRangeMaskLumMax': 'circ_grad_based_corr_correction_range_mask_lum_max',
            'CircGradBasedCorrCorrectionRangeMaskLumMin': 'circ_grad_based_corr_correction_range_mask_lum_min',
            'CircGradBasedCorrCorrectionRangeMaskType': 'circ_grad_based_corr_correction_range_mask_type',
            'CircGradBasedCorrDefringe': 'circ_grad_based_corr_defringe',
            'CircGradBasedCorrExposure2012': 'circ_grad_based_corr_exposure_2012',
            'CircGradBasedCorrHighlights2012': 'circ_grad_based_corr_highlights_2012',
            'CircGradBasedCorrHue': 'circ_grad_based_corr_hue',
            'CircGradBasedCorrLuminanceNoise': 'circ_grad_based_corr_luminance_noise',
            'CircGradBasedCorrMaskAngle': 'circ_grad_based_corr_mask_angle',
            'CircGradBasedCorrMaskBottom': 'circ_grad_based_corr_mask_bottom',
            'CircGradBasedCorrMaskFeather': 'circ_grad_based_corr_mask_feather',
            'CircGradBasedCorrMaskFlipped': 'circ_grad_based_corr_mask_flipped',
            'CircGradBasedCorrMaskLeft': 'circ_grad_based_corr_mask_left',
            'CircGradBasedCorrMaskMidpoint': 'circ_grad_based_corr_mask_midpoint',
            'CircGradBasedCorrMaskRight': 'circ_grad_based_corr_mask_right',
            'CircGradBasedCorrMaskRoundness': 'circ_grad_based_corr_mask_roundness',
            'CircGradBasedCorrMaskTop': 'circ_grad_based_corr_mask_top',
            'CircGradBasedCorrMaskValue': 'circ_grad_based_corr_mask_value',
            'CircGradBasedCorrMaskVersion': 'circ_grad_based_corr_mask_version',
            'CircGradBasedCorrMaskWhat': 'circ_grad_based_corr_mask_what',
            'CircGradBasedCorrMoire': 'circ_grad_based_corr_moire',
            'CircGradBasedCorrSaturation': 'circ_grad_based_corr_saturation',
            'CircGradBasedCorrShadows2012': 'circ_grad_based_corr_shadows_2012',
            'CircGradBasedCorrSharpness': 'circ_grad_based_corr_sharpness',
            'CircGradBasedCorrTemperature': 'circ_grad_based_corr_temperature',
            'CircGradBasedCorrTint': 'circ_grad_based_corr_tint',
            'CircGradBasedCorrWhat': 'circ_grad_based_corr_what',
            'CircleOfConfusion': 'circle_of_confusion',
            'Clarity2012': 'clarity_2012',
            'CMMFlags': 'cmm_flags',
            'CodedCharacterSet': 'coded_character_set',
            'ColorCompensationFilter': 'color_compensation_filter',
            'ColorDataVersion': 'color_data_version',
            'ColorMatrix': 'color_matrix',
            'ColorMatrix1': 'color_matrix_1',
            'ColorMatrix2': 'color_matrix_2',
            'ColorMode': 'color_mode',
            'ColorNoiseReduction': 'color_noise_reduction',
            'ColorNoiseReductionDetail': 'color_noise_reduction_detail',
            'ColorNoiseReductionSmoothness': 'color_noise_reduction_smoothness',
            'ColorSpace': 'color_space',
            'ColorSpaceData': 'color_space_data',
            'ColorTempAsShot': 'color_temp_as_shot',
            'ColorTempAuto': 'color_temp_auto',
            'ColorTempCloudy': 'color_temp_cloudy',
            'ColorTempDaylight': 'color_temp_daylight',
            'ColorTemperature': 'color_temperature',
            'ColorTempFlash': 'color_temp_flash',
            'ColorTempFluorescent': 'color_temp_fluorescent',
            'ColorTempKelvin': 'color_temp_kelvin',
            'ColorTempMeasured': 'color_temp_measured',
            'ColorTempShade': 'color_temp_shade',
            'ColorTempTungsten': 'color_temp_tungsten',
            'ColorTone': 'color_tone',
            'ComponentsConfiguration': 'components_configuration',
            'CompressedBitsPerPixel': 'compressed_bits_per_pixel',
            'Compression': 'compression',
            'ConnectionSpaceIlluminant': 'connection_space_illuminant',
            'ContinuousDrive': 'continuous_drive',
            'Contrast': 'contrast',
            'Contrast2012': 'contrast_2012',
            'ControlMode': 'control_mode',
            'ConvertToGrayscale': 'convert_to_grayscale',
            'Copyright': 'copyright',
            'CR2CFAPattern': 'cr2_cfa_pattern',
            'CreateDate': 'create_date',
            'CreativeStyle': 'creative_style',
            'Creator': 'creator',
            'CreatorTool': 'creator_tool',
            'CropAngle': 'crop_angle',
            'CropBottom': 'crop_bottom',
            'CropBottomMargin': 'crop_bottom_margin',
            'CropConstrainToWarp': 'crop_constrain_to_warp',
            'CropLeft': 'crop_left',
            'CropLeftMargin': 'crop_left_margin',
            'CroppedImageHeight': 'cropped_image_height',
            'CroppedImageLeft': 'cropped_image_left',
            'CroppedImageTop': 'cropped_image_top',
            'CroppedImageWidth': 'cropped_image_width',
            'CropRight': 'crop_right',
            'CropRightMargin': 'crop_right_margin',
            'CropTop': 'crop_top',
            'CropTopMargin': 'crop_top_margin',
            'CurrentIPTCDigest': 'current_iptc_digest',
            'CustomControls': 'custom_controls',
            'CustomPictureStyleFileName': 'custom_picture_style_file_name',
            'CustomRendered': 'custom_rendered',
            'DateCreated': 'date_created',
            'DateTimeCreated': 'date_time_created',
            'DateTimeOriginal': 'date_time_original',
            'DaylightSavings': 'daylight_savings',
            'DefaultCropOrigin': 'default_crop_origin',
            'DefaultCropSize': 'default_crop_size',
            'DefaultEraseOption': 'default_erase_option',
            'DefaultScale': 'default_scale',
            'DefaultUserCrop': 'default_user_crop',
            'DefringeGreenAmount': 'defringe_green_amount',
            'DefringeGreenHueHi': 'defringe_green_hue_hi',
            'DefringeGreenHueLo': 'defringe_green_hue_lo',
            'DefringePurpleAmount': 'defringe_purple_amount',
            'DefringePurpleHueHi': 'defringe_purple_hue_hi',
            'DefringePurpleHueLo': 'defringe_purple_hue_lo',
            'Dehaze': 'dehaze',
            'DerivedFromDocumentID': 'derived_from_document_id',
            'DerivedFromInstanceID': 'derived_from_instance_id',
            'DerivedFromOriginalDocumentID': 'derived_from_original_document_id',
            'Description': 'description',
            'DeviceAttributes': 'device_attributes',
            'DeviceManufacturer': 'device_manufacturer',
            'DeviceMfgDesc': 'device_mfg_desc',
            'DeviceModel': 'device_model',
            'DeviceModelDesc': 'device_model_desc',
            'DialDirectionTvAv': 'dial_direction_tv_av',
            'DigitalGain': 'digital_gain',
            'DigitalZoom': 'digital_zoom',
            'DigitalZoomRatio': 'digital_zoom_ratio',
            'Directory': 'directory',
            'DisplayedUnitsX': 'displayed_units_x',
            'DisplayedUnitsY': 'displayed_units_y',
            'DistortionCorrection': 'distortion_correction',
            'DistortionCorrectionSetting': 'distortion_correction_setting',
            'DistortionCorrParams': 'distortion_corr_params',
            'DistortionCorrParamsNumber': 'distortion_corr_params_number',
            'DistortionCorrParamsPresent': 'distortion_corr_params_present',
            'DNGBackwardVersion': 'dng_backward_version',
            'DNGPrivateData': 'dng_private_data',
            'DNGVersion': 'dng_version',
            'DocumentID': 'document_id',
            'DriveMode': 'drive_mode',
            'DustRemovalData': 'dust_removal_data',
            'DynamicRangeOptimizer': 'dynamic_range_optimizer',
            'EasyMode': 'easy_mode',
            'ElectronicFrontCurtainShutter': 'electronic_front_curtain_shutter',
            'ExifByteOrder': 'exif_byte_order',
            'ExifImageHeight': 'exif_image_height',
            'ExifImageWidth': 'exif_image_width',
            'ExifToolVersion': 'exiftool_version',
            'ExifVersion': 'exif_version',
            'Exposure2012': 'exposure_2012',
            'ExposureCompensation': 'exposure_compensation',
            'ExposureLevelIncrements': 'exposure_level_increments',
            'ExposureMode': 'exposure_mode',
            'ExposureProgram': 'exposure_program',
            'ExposureStandardAdjustment': 'exposure_standard_adjustment',
            'ExposureTime': 'exposure_time',
            'FaceInfoLength': 'face_info_length',
            'FaceInfoOffset': 'face_info_offset',
            'FacesDetected': 'faces_detected',
            'FileAccessDate': 'file_access_date',
            'FileFormat': 'file_format',
            'FileInodeChangeDate': 'file_inode_change_date',
            'FileModifyDate': 'file_modify_date',
            'FileName': 'filename',
            'FilePermissions': 'file_permissions',
            'FileSize': 'file_size',
            'FileSource': 'file_source',
            'FileType': 'file_type',
            'FileTypeExtension': 'file_type_extension',
            'Flash': 'flash',
            'FlashAction': 'flash_action',
            'FlashActivity': 'flash_activity',
            'FlashBits': 'flash_bits',
            'FlashExposureComp': 'flash_exposure_comp',
            'FlashExposureLock': 'flash_exposure_lock',
            'FlashGuideNumber': 'flash_guide_number',
            'FlashLevel': 'flash_level',
            'FlashMode': 'flash_mode',
            'FlashpixVersion': 'flashpix_version',
            'FlashStatus': 'flash_status',
            'FlexibleSpotPosition': 'flexible_spot_position',
            'FlightPitchDegree': 'flight_pitch_degree',
            'FlightRollDegree': 'flight_roll_degree',
            'FlightYawDegree': 'flight_yaw_degree',
            'FNumber': 'f_number',
            'FocalLength': 'focal_length',
            'FocalLength35efl': 'focal_length_35_efl',
            'FocalLengthIn35mmFormat': 'focal_length_in_35mm_format',
            'FocalPlaneAFPointsUsed': 'focal_plane_af_points_used',
            'FocalPlaneResolutionUnit': 'focal_plane_resolution_unit',
            'FocalPlaneXResolution': 'focal_plane_x_resolution',
            'FocalPlaneYResolution': 'focal_plane_y_resolution',
            'FocalUnits': 'focal_units',
            'FocusDistance2': 'focus_distance2',
            'FocusLocation': 'focus_location',
            'FocusMode': 'focus_mode',
            'FocusPosition2': 'focus_position2',
            'FocusRange': 'focus_range',
            'Format': 'format',
            'FOV': 'field_of_view',
            'FullImageSize': 'full_image_size',
            'GainControl': 'gain_control',
            'GimbalPitchDegree': 'gimbal_pitch_degree',
            'GimbalReverse': 'gimbal_reverse',
            'GimbalRollDegree': 'gimbal_roll_degree',
            'GimbalYawDegree': 'gimbal_yaw_degree',
            'GlobalAltitude': 'global_altitude',
            'GlobalAngle': 'global_angle',
            'GPSAltitude': 'gps_altitude',
            'GPSAltitudeRef': 'gps_altitude_ref',
            'GPSLatitude': 'gps_latitude',
            'GPSLatitudeRef': 'gps_latitude_ref',
            'GPSLongitude': 'gps_longitude',
            'GPSLongitudeRef': 'gps_longitude_ref',
            'GPSMapDatum': 'gps_map_datum',
            'GPSPosition': 'gps_position',
            'GPSSatellites': 'gps_satellites',
            'GPSStatus': 'gps_status',
            'GPSVersionID': 'gps_version_id',
            'GradientBasedCorrActive': 'gradient_based_corr_active',
            'GradientBasedCorrAmount': 'gradient_based_corr_amount',
            'GradientBasedCorrClarity2012': 'gradient_based_corr_clarity_2012',
            'GradientBasedCorrContrast': 'gradient_based_corr_contrast',
            'GradientBasedCorrCorrectionRangeMaskColorAmount': 'gradient_based_corr_correction_range_mask_color_amount',
            'GradientBasedCorrCorrectionRangeMaskLumFeather': 'gradient_based_corr_correction_range_mask_lum_feather',
            'GradientBasedCorrCorrectionRangeMaskLumMax': 'gradient_based_corr_correction_range_mask_lum_max',
            'GradientBasedCorrCorrectionRangeMaskLumMin': 'gradient_based_corr_correction_range_mask_lum_min',
            'GradientBasedCorrCorrectionRangeMaskType': 'gradient_based_corr_correction_range_mask_type',
            'GradientBasedCorrDefringe': 'gradient_based_corr_defringe',
            'GradientBasedCorrExposure2012': 'gradient_based_corr_exposure_2012',
            'GradientBasedCorrHighlights2012': 'gradient_based_corr_highlights_2012',
            'GradientBasedCorrHue': 'gradient_based_corr_hue',
            'GradientBasedCorrLuminanceNoise': 'gradient_based_corr_luminance_noise',
            'GradientBasedCorrMaskFullX': 'gradient_based_corr_mask_full_x',
            'GradientBasedCorrMaskFullY': 'gradient_based_corr_mask_full_y',
            'GradientBasedCorrMaskValue': 'gradient_based_corr_mask_value',
            'GradientBasedCorrMaskWhat': 'gradient_based_corr_mask_what',
            'GradientBasedCorrMaskZeroX': 'gradient_based_corr_mask_zero_x',
            'GradientBasedCorrMaskZeroY': 'gradient_based_corr_mask_zero_y',
            'GradientBasedCorrMoire': 'gradient_based_corr_moire',
            'GradientBasedCorrSaturation': 'gradient_based_corr_saturation',
            'GradientBasedCorrShadows2012': 'gradient_based_corr_shadows_2012',
            'GradientBasedCorrSharpness': 'gradient_based_corr_sharpness',
            'GradientBasedCorrTemperature': 'gradient_based_corr_temperature',
            'GradientBasedCorrTint': 'gradient_based_corr_tint',
            'GradientBasedCorrWhat': 'gradient_based_corr_what',
            'GrainAmount': 'grain_amount',
            'GreenHue': 'green_hue',
            'GreenMatrixColumn': 'green_matrix_column',
            'GreenSaturation': 'green_saturation',
            'GreenTRC': 'green_trc',
            'HasCrop': 'has_crop',
            'HasRealMergedData': 'has_real_merged_data',
            'HasSettings': 'has_settings',
            'HDR': 'hdr',
            'HDREffect': 'hdr_effect',
            'HDRSetting': 'hdr_setting',
            'Height': 'height',
            'HighISONoiseReduction': 'high_iso_noise_reduction',
            'HighISONoiseReduction2': 'high_iso_noise_reduction_2',
            'Highlights2012': 'highlights_2012',
            'HighlightTonePriority': 'highlight_tone_priority',
            'HistoryAction': 'history_action',
            'HistoryChanged': 'history_changed',
            'HistoryInstanceID': 'history_instance_id',
            'HistoryParameters': 'history_parameters',
            'HistorySoftwareAgent': 'history_software_agent',
            'HistoryWhen': 'history_when',
            'HueAdjustmentAqua': 'hue_adjustment_aqua',
            'HueAdjustmentBlue': 'hue_adjustment_blue',
            'HueAdjustmentGreen': 'hue_adjustment_green',
            'HueAdjustmentMagenta': 'hue_adjustment_magenta',
            'HueAdjustmentOrange': 'hue_adjustment_orange',
            'HueAdjustmentPurple': 'hue_adjustment_purple',
            'HueAdjustmentRed': 'hue_adjustment_red',
            'HueAdjustmentYellow': 'hue_adjustment_yellow',
            'HyperfocalDistance': 'hyperfocal_distance',
            'ImageDescription': 'image_description',
            'ImageHeight': 'image_height',
            'ImageSize': 'image_size',
            'ImageStabilization': 'image_stabilization',
            'ImageWidth': 'image_width',
            'IncrementalTemperature': 'incremental_temperature',
            'IncrementalTint': 'incremental_tint',
            'InstanceID': 'instance_id',
            'IntelligentAuto': 'intelligent_auto',
            'InternalSerialNumber': 'internal_serial_number',
            'InteropIndex': 'interop_index',
            'InteropVersion': 'interop_version',
            'IPTCDigest': 'iptc_digest',
            'ISO': 'iso',
            'Iso': 'iso',
            'ISOAutoMax': 'iso_auto_max',
            'ISOAutoMin': 'iso_auto_min',
            'ISOSetting': 'iso_setting',
            'ISOSpeedIncrements': 'iso_speed_increments',
            'Label': 'label',
            'LateralChromaticAberration': 'lateral_chromatic_aberration',
            'LayerCount': 'layer_count',
            'Lens': 'lens',
            'Lens35efl': 'lens35efl',
            'LensDriveWhenAFImpossible': 'lens_drive_when_af_impossible',
            'LensE': 'lens_e',
            'LensE-mountVersion': 'lens_e_mount_version',
            'LensFirmwareVersion': 'lens_firmware_version',
            'LensFormat': 'lens_format',
            'LensID': 'lens_id',
            'LensInfo': 'lens_info',
            'LensManualDistortionAmount': 'lens_manual_distortion_amount',
            'LensModel': 'lens_model',
            'LensMount': 'lens_mount',
            'LensMount2': 'lens_mount2',
            'LensProfileChromaticAberrationScale': 'lens_profile_chromatic_aberration_scale',
            'LensProfileDigest': 'lens_profile_digest',
            'LensProfileDistortionScale': 'lens_profile_distortion_scale',
            'LensProfileEnable': 'lens_profile_enable',
            'LensProfileFilename': 'lens_profile_filename',
            'LensProfileName': 'lens_profile_name',
            'LensProfileSetup': 'lens_profile_setup',
            'LensProfileVignettingScale': 'lens_profile_vignetting_scale',
            'LensSerialNumber': 'lens_serial_number',
            'LensSpec': 'lens_spec',
            'LensSpecFeatures': 'lens_spec_features',
            'LensType': 'lens_type',
            'LensType2': 'lens_type2',
            'LensType3': 'lens_type3',
            'LensZoomPosition': 'lens_zoom_position',
            'LightSource': 'light_source',
            'LightValue': 'light_value',
            'LinearityUpperMargin': 'linearity_upper_margin',
            'LinearResponseLimit': 'linear_response_limit',
            'LiveViewShooting': 'live_view_shooting',
            'LongExposureNoiseReduction': 'long_exposure_noise_reduction',
            'LuminanceAdjustmentAqua': 'luminance_adjustment_aqua',
            'LuminanceAdjustmentBlue': 'luminance_adjustment_blue',
            'LuminanceAdjustmentGreen': 'luminance_adjustment_green',
            'LuminanceAdjustmentMagenta': 'luminance_adjustment_magenta',
            'LuminanceAdjustmentOrange': 'luminance_adjustment_orange',
            'LuminanceAdjustmentPurple': 'luminance_adjustment_purple',
            'LuminanceAdjustmentRed': 'luminance_adjustment_red',
            'LuminanceAdjustmentYellow': 'luminance_adjustment_yellow',
            'LuminanceSmoothing': 'luminance_smoothing',
            'LVShootingAreaDisplay': 'lv_shooting_area_display',
            'MacroMode': 'macro_mode',
            'Make': 'make',
            'MakeAndModel': 'make_and_model',
            'ManualAFPointSelPattern': 'manual_af_point_sel_pattern',
            'ManualFlashOutput': 'manual_flash_output',
            'MaxAperture': 'max_aperture',
            'MaxApertureValue': 'max_aperture_value',
            'MaxFocalLength': 'max_focal_length',
            'MeasuredEV': 'measured_ev',
            'MeasuredEV2': 'measured_ev2',
            'MeasuredRGGB': 'measured_rggb',
            'MediaWhitePoint': 'media_white_point',
            'Megapixels': 'megapixels',
            'MetadataDate': 'metadata_date',
            'MetaVersion': 'meta_version',
            'MeteringMode': 'metering_mode',
            'MeteringMode2': 'metering_mode_2',
            'MIMEType': 'mime_type',
            'MinAperture': 'min_aperture',
            'MinFocalLength': 'min_focal_length',
            'Model': 'model',
            'ModelReleaseYear': 'model_release_year',
            'ModifyDate': 'modify_date',
            'MultiExposure': 'multi_exposure',
            'MultiExposureControl': 'multi_exposure_control',
            'MultiExposureShots': 'multi_exposure_shots',
            'MultiFrameNoiseReduction': 'multi_frame_noise_reduction',
            'MultiFrameNREffect': 'multi_frame_n_r_effect',
            'NDFilter': 'nd_filter',
            'NoiseProfile': 'noise_profile',
            'NormalWhiteLevel': 'normal_white_level',
            'NumAFPoints': 'num_af_points',
            'NumChannels': 'num_channels',
            'NumSlices': 'num_slices',
            'ObjectName': 'object_name',
            'OffsetTime': 'offset_time',
            'OffsetTimeDigitized': 'offset_time_digitized',
            'OffsetTimeOriginal': 'offset_time_original',
            'OneShotAFRelease': 'one_shot_af_release',
            'OpcodeList3': 'opcode_list_3',
            'OpticalZoomCode': 'optical_zoom_code',
            'Orientation': 'orientation',
            'OrientationLinkedAF': 'orientation_linked_af',
            'OriginalBestQualitySize': 'original_best_quality_size',
            'OriginalDefaultCropSize': 'original_default_crop_size',
            'OriginalDefaultFinalSize': 'original_default_final_size',
            'OriginalDocumentID': 'original_document_id',
            'OwnerName': 'owner_name',
            'PaintCorrectionActive': 'paint_correction_active',
            'PaintCorrectionAmount': 'paint_correction_amount',
            'PaintCorrectionBrightness': 'paint_correction_brightness',
            'PaintCorrectionClarity': 'paint_correction_clarity',
            'PaintCorrectionClarity2012': 'paint_correction_clarity2012',
            'PaintCorrectionContrast': 'paint_correction_contrast',
            'PaintCorrectionContrast2012': 'paint_correction_contrast2012',
            'PaintCorrectionCorrectionRangeMaskColorAmount': 'paint_correction_correction_range_mask_color_amount',
            'PaintCorrectionCorrectionRangeMaskLumFeather': 'paint_correction_correction_range_mask_lum_feather',
            'PaintCorrectionCorrectionRangeMaskLumMax': 'paint_correction_correction_range_mask_lum_max',
            'PaintCorrectionCorrectionRangeMaskLumMin': 'paint_correction_correction_range_mask_lum_min',
            'PaintCorrectionCorrectionRangeMaskType': 'paint_correction_correction_range_mask_type',
            'PaintCorrectionDefringe': 'paint_correction_defringe',
            'PaintCorrectionExposure': 'paint_correction_exposure',
            'PaintCorrectionExposure2012': 'paint_correction_exposure2012',
            'PaintCorrectionHighlights2012': 'paint_correction_highlights2012',
            'PaintCorrectionHue': 'paint_correction_hue',
            'PaintCorrectionLocalBlacks2012': 'paint_correction_local_blacks2012',
            'PaintCorrectionLocalDehaze': 'paint_correction_local_dehaze',
            'PaintCorrectionLocalWhites2012': 'paint_correction_local_whites2012',
            'PaintCorrectionLuminanceNoise': 'paint_correction_luminance_noise',
            'PaintCorrectionMaskCenterWeight': 'paint_correction_mask_center_weight',
            'PaintCorrectionMaskDabs': 'paint_correction_mask_dabs',
            'PaintCorrectionMaskFlow': 'paint_correction_mask_flow',
            'PaintCorrectionMaskRadius': 'paint_correction_mask_radius',
            'PaintCorrectionMaskValue': 'paint_correction_mask_value',
            'PaintCorrectionMaskWhat': 'paint_correction_mask_what',
            'PaintCorrectionMoire': 'paint_correction_moire',
            'PaintCorrectionSaturation': 'paint_correction_saturation',
            'PaintCorrectionShadows2012': 'paint_correction_shadows2012',
            'PaintCorrectionSharpness': 'paint_correction_sharpness',
            'PaintCorrectionTemperature': 'paint_correction_temperature',
            'PaintCorrectionTint': 'paint_correction_tint',
            'PaintCorrectionWhat': 'paint_correction_what',
            'ParametricDarks': 'parametric_darks',
            'ParametricHighlights': 'parametric_highlights',
            'ParametricHighlightSplit': 'parametric_highlight_split',
            'ParametricLights': 'parametric_lights',
            'ParametricMidtoneSplit': 'parametric_midtone_split',
            'ParametricShadows': 'parametric_shadows',
            'ParametricShadowSplit': 'parametric_shadow_split',
            'PerChannelBlackLevel': 'per_channel_black_level',
            'PeripheralIlluminationCorr': 'peripheral_illumination_corr',
            'PeripheralLightingSetting': 'peripheral_lighting_setting',
            'PerspectiveAspect': 'perspective_aspect',
            'PerspectiveHorizontal': 'perspective_horizontal',
            'PerspectiveRotate': 'perspective_rotate',
            'PerspectiveScale': 'perspective_scale',
            'PerspectiveUpright': 'perspective_upright',
            'PerspectiveVertical': 'perspective_vertical',
            'PerspectiveX': 'perspective_x',
            'PerspectiveY': 'perspective_y',
            'PhotometricInterpretation': 'photometric_interpretation',
            'PhotoshopThumbnail': 'photoshop_thumbnail',
            'PictureEffect': 'picture_effect',
            'PictureEffect2': 'picture_effect_2',
            'PictureProfile': 'picture_profile',
            'PictureStyle': 'picture_style',
            'PictureStylePC': 'picture_style_pc',
            'PictureStyleUserDef': 'picture_style_user_def',
            'PixelAspectRatio': 'pixel_aspect_ratio',
            'PlanarConfiguration': 'planar_configuration',
            'PostCropVignetteAmount': 'post_crop_vignette_amount',
            'PreviewImage': 'preview_image',
            'PreviewImageLength': 'preview_image_length',
            'PreviewImageSize': 'preview_image_size',
            'PreviewImageStart': 'preview_image_start',
            'PrimaryPlatform': 'primary_platform',
            'PrintIMVersion': 'print_i_m_version',
            'PrintPosition': 'print_position',
            'PrintScale': 'print_scale',
            'PrintStyle': 'print_style',
            'PrioritySetInAWB': 'priority_set_in_awb',
            'ProcessVersion': 'process_version',
            'ProfileClass': 'profile_class',
            'ProfileCMMType': 'profile_cmm_type',
            'ProfileConnectionSpace': 'profile_connection_space',
            'ProfileCopyright': 'profile_copyright',
            'ProfileCreator': 'profile_creator',
            'ProfileDateTime': 'profile_date_time',
            'ProfileDescription': 'profile_description',
            'ProfileEmbedPolicy': 'profile_embed_policy',
            'ProfileFileSignature': 'profile_file_signature',
            'ProfileHueSatMapData1': 'profile_hue_sat_map_data_1',
            'ProfileHueSatMapData2': 'profile_hue_sat_map_data_2',
            'ProfileHueSatMapDims': 'profile_hue_sat_map_dims',
            'ProfileID': 'profile_id',
            'ProfileName': 'profile_name',
            'ProfileVersion': 'profile_version',
            'Quality': 'quality',
            'Quality2': 'quality_2',
            'Rating': 'rating',
            'RawFileName': 'raw_file_name',
            'RAWFileType': 'raw_file_type',
            'RawImageSegmentation': 'raw_image_segmentation',
            'RawJpgSize': 'raw_jpg_size',
            'ReaderName': 'reader_name',
            'RecommendedExposureIndex': 'recommended_exposure_index',
            'RecordMode': 'record_mode',
            'RedBalance': 'red_balance',
            'RedHue': 'red_hue',
            'RedMatrixColumn': 'red_matrix_column',
            'RedSaturation': 'red_saturation',
            'RedTRC': 'red_trc',
            'ReferenceBlackWhite': 'reference_black_white',
            'RelativeAltitude': 'relative_altitude',
            'ReleaseMode': 'release_mode',
            'ReleaseMode2': 'release_mode_2',
            'ReleaseMode3': 'release_mode_3',
            'RenderingIntent': 'rendering_intent',
            'ResolutionUnit': 'resolution_unit',
            'RetractLensOnPowerOff': 'retract_lens_on_power_off',
            'RowsPerStrip': 'rows_per_strip',
            'SafetyShift': 'safety_shift',
            'SameExposureForNewAperture': 'same_exposure_for_new_aperture',
            'SamplesPerPixel': 'samples_per_pixel',
            'Saturation': 'saturation',
            'SaturationAdjustmentAqua': 'saturation_adjustment_aqua',
            'SaturationAdjustmentBlue': 'saturation_adjustment_blue',
            'SaturationAdjustmentGreen': 'saturation_adjustment_green',
            'SaturationAdjustmentMagenta': 'saturation_adjustment_magenta',
            'SaturationAdjustmentOrange': 'saturation_adjustment_orange',
            'SaturationAdjustmentPurple': 'saturation_adjustment_purple',
            'SaturationAdjustmentRed': 'saturation_adjustment_red',
            'SaturationAdjustmentYellow': 'saturation_adjustment_yellow',
            'ScaleFactor35efl': 'scale_factor_35_efl',
            'SceneCaptureType': 'scene_capture_type',
            'SceneMode': 'scene_mode',
            'SceneType': 'scene_type',
            'SelectAFAreaSelectionMode': 'select_af_area_selection_mode',
            'SelfData': 'self_data',
            'SelfTimer': 'self_timer',
            'SensitivityType': 'sensitivity_type',
            'SensorBlueLevel': 'sensor_blue_level',
            'SensorBottomBorder': 'sensor_bottom_border',
            'SensorHeight': 'sensor_height',
            'SensorLeftBorder': 'sensor_left_border',
            'SensorRedLevel': 'sensor_red_level',
            'SensorRightBorder': 'sensor_right_border',
            'SensorTopBorder': 'sensor_top_border',
            'SensorWidth': 'sensor_width',
            'SequenceFileNumber': 'sequence_file_number',
            'SequenceImageNumber': 'sequence_image_number',
            'SequenceLength': 'sequence_length',
            'SequenceNumber': 'sequence_number',
            'SerialNumber': 'serial_number',
            'Shadows2012': 'shadows_2012',
            'ShadowScale': 'shadow_scale',
            'ShadowTint': 'shadow_tint',
            'SharpenDetail': 'sharpen_detail',
            'SharpenEdgeMasking': 'sharpen_edge_masking',
            'SharpenRadius': 'sharpen_radius',
            'Sharpness': 'sharpness',
            'SharpnessFrequency': 'sharpness_frequency',
            'ShootingMode': 'shooting_mode',
            'ShotNumberSincePowerUp': 'shot_number_since_power_up',
            'Shutter': 'shutter',
            'ShutterCount': 'shutter_count',
            'ShutterCount2': 'shutter_count2',
            'ShutterCount3': 'shutter_count3',
            'ShutterSpeed': 'shutter_speed',
            'ShutterSpeedRange': 'shutter_speed_range',
            'ShutterSpeedValue': 'shutter_speed_value',
            'SlicesGroupName': 'slices_group_name',
            'SlowShutter': 'slow_shutter',
            'SoftSkinEffect': 'soft_skin_effect',
            'Software': 'software',
            'SonyDateTime': 'sony_date_time',
            'SonyExposureTime': 'sony_exposure_time',
            'SonyExposureTime2': 'sony_exposure_time_2',
            'SonyFNumber': 'sony_f_number',
            'SonyImageHeight': 'sony_image_height',
            'SonyImageHeightMax': 'sony_image_height_max',
            'SonyImageWidth': 'sony_image_width',
            'SonyImageWidthMax': 'sony_image_width_max',
            'SonyISO': 'sony_iso',
            'SonyMaxApertureValue': 'sony_max_aperture_value',
            'SonyModelID': 'sony_model_id',
            'SonyRawFileType': 'sony_raw_file_type',
            'SonyTimeMinSec': 'sony_time_min_sec',
            'SonyToneCurve': 'sony_tone_curve',
            'SpecularWhiteLevel': 'specular_white_level',
            'SplitToningBalance': 'split_toning_balance',
            'SplitToningHighlightHue': 'split_toning_highlight_hue',
            'SplitToningHighlightSaturation': 'split_toning_highlight_saturation',
            'SplitToningShadowHue': 'split_toning_shadow_hue',
            'SplitToningShadowSaturation': 'split_toning_shadow_saturation',
            'SR2SubIFDKey': 'sr2_sub_ifd_key',
            'SR2SubIFDLength': 'sr2_sub_ifd_length',
            'SR2SubIFDOffset': 'sr2_sub_ifd_offset',
            'SRAWQuality': 's_raw_quality',
            'SRawType': 's_raw_type',
            'StopsAboveBaseISO': 'stops_above_base_iso',
            'StripByteCounts': 'strip_byte_counts',
            'StripOffsets': 'strip_offsets',
            'SubfileType': 'subfile_type',
            'SubSecCreateDate': 'sub_sec_create_date',
            'SubSecDateTimeOriginal': 'sub_sec_date_time_original',
            'SubSecModifyDate': 'sub_sec_modify_date',
            'SubSecTime': 'sub_sec_time',
            'SubSecTimeDigitized': 'sub_sec_time_digitized',
            'SubSecTimeOriginal': 'sub_sec_time_original',
            'TargetAperture': 'target_aperture',
            'TargetExposureTime': 'target_exposure_time',
            'ThumbnailImage': 'thumbnail_image',
            'ThumbnailImageValidArea': 'thumbnail_image_valid_area',
            'ThumbnailLength': 'thumbnail_length',
            'ThumbnailOffset': 'thumbnail_offset',
            'TiffMeteringImage': 'tiff_metering_image',
            'TiffMeteringImageHeight': 'tiff_metering_image_height',
            'TiffMeteringImageWidth': 'tiff_metering_image_width',
            'TimeCreated': 'time_created',
            'TimeZone': 'time_zone',
            'TimeZoneCity': 'time_zone_city',
            'Tint': 'tint',
            'Title': 'title',
            'ToneCurve': 'tone_curve',
            'ToneCurveBlue': 'tone_curve_blue',
            'ToneCurveGreen': 'tone_curve_green',
            'ToneCurveName': 'tone_curve_name',
            'ToneCurveName2012': 'tone_curve_name_2012',
            'ToneCurvePV2012': 'tone_curve_pv_2012',
            'ToneCurvePV2012Blue': 'tone_curve_pv_2012_blue',
            'ToneCurvePV2012Green': 'tone_curve_pv_2012_green',
            'ToneCurvePV2012Red': 'tone_curve_pv_2012_red',
            'ToneCurveRed': 'tone_curve_red',
            'toolkit': 'toolkit',
            'Transformation': 'transformation',
            'UniqueCameraModel': 'unique_camera_model',
            'UprightCenterMode': 'upright_center_mode',
            'UprightCenterNormX': 'upright_center_norm_x',
            'UprightCenterNormY': 'upright_center_norm_y',
            'UprightFocalLength35mm': 'upright_focal_length_35mm',
            'UprightFocalMode': 'upright_focal_mode',
            'UprightFourSegmentsCount': 'upright_four_segments_count',
            'UprightPreview': 'upright_preview',
            'UprightTransformCount': 'upright_transform_count',
            'UprightVersion': 'upright_version',
            'URL_List': 'url_list',
            'UserComment': 'user_comment',
            'USMLensElectronicMF': 'usm_lens_electronic_mf',
            'ValidAFPoints': 'valid_af_points',
            'VariableLowPassFilter': 'variable_low_pass_filter',
            'Version': 'version',
            'VFDisplayIllumination': 'vf_display_illumination',
            'Vibrance': 'vibrance',
            'ViewfinderWarnings': 'viewfinder_warnings',
            'VignetteAmount': 'vignette_amount',
            'VignettingCorrection': 'vignetting_correction',
            'VignettingCorrParams': 'vignetting_corr_params',
            'VignettingCorrVersion': 'vignetting_corr_version',
            'VirtualFocalLength': 'virtual_focal_length',
            'VirtualImageXCenter': 'virtual_image_x_center',
            'VirtualImageYCenter': 'virtual_image_y_center',
            'VRDOffset': 'vrd_offset',
            'WB_RGBLevels': 'wb_rgb_levels',
            'WB_RGBLevels2500K': 'wb_rgb_levels_2500k',
            'WB_RGBLevels3200K': 'wb_rgb_levels_3200k',
            'WB_RGBLevels4500K': 'wb_rgb_levels_4500k',
            'WB_RGBLevels6000K': 'wb_rgb_levels_6000k',
            'WB_RGBLevels8500K': 'wb_rgb_levels_8500k',
            'WB_RGBLevelsCloudy': 'wb_rgb_levels_cloudy',
            'WB_RGBLevelsDaylight': 'wb_rgb_levels_daylight',
            'WB_RGBLevelsFlash': 'wb_rgb_levels_flash',
            'WB_RGBLevelsFluorescent': 'wb_rgb_levels_fluorescent',
            'WB_RGBLevelsFluorescentM1': 'wb_rgb_levels_fluorescent_m1',
            'WB_RGBLevelsFluorescentP1': 'wb_rgb_levels_fluorescent_p1',
            'WB_RGBLevelsFluorescentP2': 'wb_rgb_levels_fluorescent_p2',
            'WB_RGBLevelsShade': 'wb_rgb_levels_shade',
            'WB_RGBLevelsTungsten': 'wb_rgb_levels_tungsten',
            'WB_RGGBLevels': 'wb_rggb_levels',
            'WB_RGGBLevelsAsShot': 'wb_rggb_levels_as_shot',
            'WB_RGGBLevelsAuto': 'wb_rggb_levels_auto',
            'WB_RGGBLevelsCloudy': 'wb_rggb_levels_cloudy',
            'WB_RGGBLevelsDaylight': 'wb_rggb_levels_daylight',
            'WB_RGGBLevelsFlash': 'wb_rggb_levels_flash',
            'WB_RGGBLevelsFluorescent': 'wb_rggb_levels_fluorescent',
            'WB_RGGBLevelsKelvin': 'wb_rggb_levels_kelvin',
            'WB_RGGBLevelsMeasured': 'wb_rggb_levels_measured',
            'WB_RGGBLevelsShade': 'wb_rggb_levels_shade',
            'WB_RGGBLevelsTungsten': 'wb_rggb_levels_tungsten',
            'WBBracketMode': 'wb_bracket_mode',
            'WBBracketValueAB': 'wb_bracket_value_ab',
            'WBBracketValueGM': 'wb_bracket_value_gm',
            'WBShiftAB': 'wb_shift_ab',
            'WBShiftAB_GM': 'wb_shift_ab_gm',
            'WBShiftAB_GM_Precise': 'wb_shift_ab_gm_precise',
            'WBShiftGM': 'wb_shift_gm',
            'WhiteBalance': 'white_balance',
            'WhiteBalanceBlue': 'white_balance_blue',
            'WhiteBalanceFineTune': 'white_balance_fine_tune',
            'WhiteBalanceRed': 'white_balance_red',
            'WhiteLevel': 'white_level',
            'Whites2012': 'whites_2012',
            'Width': 'width',
            'WriterName': 'writer_name',
            'XMPToolkit': 'xmp_toolkit',
            'XResolution': 'x_resolution',
            'YCbCrCoefficients': 'y_cb_cr_coefficients',
            'YCbCrPositioning': 'y_cb_cr_positioning',
            'YCbCrSubSampling': 'y_cb_cr_sub_sampling',
            'YResolution': 'y_resolution',
            'ZoneMatching': 'zone_matching',
            'ZoomSourceWidth': 'zoom_source_width',
            'ZoomTargetWidth': 'zoom_target_width',
            'MajorBrand': 'major_brand',
            'MinorVersion': 'minor_version',
            'CompatibleBrands': 'compatible_brands',
            'MovieDataSize': 'movie_data_size',
            'MovieDataOffset': 'movie_data_offset',
            'MovieHeaderVersion': 'movie_header_version',
            'TimeScale': 'time_scale',
            'Duration': 'duration',
            'PreferredRate': 'preferred_rate',
            'PreferredVolume': 'preferred_volume',
            'MatrixStructure': 'matrix_structure',
            'PreviewTime': 'preview_time',
            'PreviewDuration': 'preview_duration',
            'PosterTime': 'poster_time',
            'SelectionTime': 'selection_time',
            'SelectionDuration': 'selection_duration',
            'CurrentTime': 'current_time',
            'NextTrackID': 'next_track_id',
            'HandlerType': 'handler_type',
            'HandlerVendorID': 'handler_vendor_id',
            'Encoder': 'encoder',
            'TrackHeaderVersion': 'track_header_version',
            'TrackCreateDate': 'track_create_date',
            'TrackModifyDate': 'track_modify_date',
            'TrackID': 'track_id',
            'TrackDuration': 'track_duration',
            'TrackLayer': 'track_layer',
            'TrackVolume': 'track_volume',
            'MediaHeaderVersion': 'media_header_version',
            'MediaCreateDate': 'media_create_date',
            'MediaModifyDate': 'media_modify_date',
            'MediaTimeScale': 'media_time_scale',
            'MediaDuration': 'media_duration',
            'MediaLanguageCode': 'media_language_code',
            'HandlerDescription': 'handler_description',
            'GraphicsMode': 'graphics_mode',
            'OpColor': 'op_color',
            'CompressorID': 'compressor_id',
            'SourceImageWidth': 'source_image_width',
            'SourceImageHeight': 'source_image_height',
            'VideoFrameRate': 'video_frame_rate',
            'AvgBitrate': 'avg_bitrate',
            'Rotation': 'rotation',
        }

        newd = {}
        not_found_keys = []
        for filename, dct in exifd.items():
            newd[filename] = pydoni.rename_dict_keys(dct, column_map)
            for exif_key in newd[filename].keys():
                if exif_key not in column_map.keys() and exif_key not in column_map.values():
                    self.logger.warn("Key not found in `column_map`: '%s'" % str(exif_key))
                    not_found_keys.append(exif_key)

        if not_found_keys:
            # Key(s) not in above column map, this means we must rename them manually from
            # ExifKeyName to exif_key_name.
            new_keynames = []
            for key in not_found_keys:
                new_key = ''
                for i, char in enumerate(key):
                    if char == char.upper() and not char.isdigit() and i > 0:
                        new_key += '_' + char
                    else:
                        new_key += char

                # Corrections
                new_key = new_key.lower()
                new_key = new_key.replace('i_d', 'id')

                new_keynames.append(new_key)

            newd[filename] = pydoni.rename_dict_keys(newd[filename], dict(zip(not_found_keys, new_keynames)))

        return newd

    def _is_valid_tag_name(self, tags):
        """
        Check EXIF tag names for illegal characters.

        :param tags: list of tag names to validate
        :type tags: list
        :return: True
        :rtype: bool
        """
        self.logger.var('tags', tags)

        illegal_chars = ['-', '_']
        for tag in tags:
            for char in illegal_chars:
                if char in tag:
                    self.logger.error("Illegal char '%s' in tag name '%s'" % (char, tag))
                    assert char not in tag

        return True

    def _is_valid_tag_message(self, tagmsg):
        """
        Determine if EXIF write was successful based on tag message.

        :param tagmsg: output tag message
        :type tagmsg: str
        :return: True if successful, False otherwise
        :rtype: bool
        """
        self.logger.var('tagmsg', tagmsg)

        if 'nothing to do' in tagmsg.lower():
            return False
        else:
            return True


class FFmpeg(object):
    """
    Wrapper for FFmpeg BASH commands.
    """
    def __init__(self):
        import os
        import pydoni
        import pydoni.sh

        self.bin = pydoni.sh.find_binary('ffmpeg')
        assert os.path.isfile(self.bin)

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.logger.logvars(locals())

    def compress(self, file, outfile=None):
        """
        Compress audiofile on system by exporting it at 32K.

        :param file: paths to file or files to compress
        :type file: str, list
        :param outfile: paths to file or files to write to. If specified, must be same length
                        as `file`. If None (default), outfile name will be generated for each file.
        :type outfile: str, list or None
        """
        import os

        self.logger.logvars(locals())

        files = pydoni.ensurelist(file)
        for f in files:
            if not os.path.isfile(f):
                self.logger.error("File does not exist: " + f)
                assert os.path.isfile(f)

        if outfile is not None:
            outfiles = pydoni.ensurelist(outfile)
            if len(files) != len(outfiles):
                self.logger.error("Specified input and output filepaths are of different lengths")
                assert len(files) == len(outfiles)

        for i, f in enumerate(files):
            tmpoutfile = pydoni.append_filename_suffix(f, '-COMPRESSED') if outfile is None else outfiles[i]
            if os.path.isfile(tmpoutfile):
                os.remove(tmpoutfile)

            try:
                cmd = '{} -i "{}" -map 0:a:0 -b:a 32k "{}"'.format(self.bin, f, tmpoutfile)
                self.logger.debug(cmd)

                pydoni.syscmd(cmd)
                self.logger.info("Compressed '%s' to '%s'" % (f, tmpoutfile))

            except Exception as e:
                if os.path.isfile(tmpoutfile):
                    os.remove(tmpoutfile)

                self.logger.exception('Failed to run FFMpeg to compress audiofile')
                raise e

    def join(self, audiofiles, outfile):
        """
        Join multiple audio files into a single audio file using a direct call to FFMpeg.

        :param audiofiles: list of audio filenames to join together
        :type audiofiles: list
        :param outfile: name of file to create from joined audio files
        :type outfile: str
        """

        import os

        self.logger.logvars(locals())

        assert isinstance(audiofiles, list)
        assert len(audiofiles) > 1

        fname_map = {}
        replace_strings = {
            "'": 'SINGLEQUOTE'
        }
        self.logger.var('replace_strings', replace_strings)

        audiofiles = [os.path.abspath(f) for f in audiofiles]
        self.logger.var('audiofiles', audiofiles)

        tmpfile = os.path.join(
            os.path.dirname(audiofiles[0]),
            '.tmp.pydoni.audio.FFmpeg.join.%s.txt' % pydoni.systime(stripchars=True))
        self.logger.var('tmpfile', tmpfile)

        with open(tmpfile, 'w') as f:
            for fname in audiofiles:
                newfname = fname
                for key, val in replace_strings.items():
                    newfname = newfname.replace(key, val)

                fname_map[fname] = newfname
                os.rename(fname, newfname)
                f.write("file '%s'\n" % newfname)

        self.logger.var('fname_map', fname_map)
        # Old command 2020-01-30 15:59:04
        # cmd = 'ffmpeg -i "concat:{}" -acodec copy "{}"'.format('|'.join(audiofiles), outfile)

        cmd = '{} -f concat -safe 0 -i "{}" -c copy "{}"'.format(self.bin, tmpfile, outfile)
        self.logger.var('cmd', cmd)
        pydoni.syscmd(cmd)

        for f, nf in fname_map.items():
            os.rename(nf, f)

        if os.path.isfile(tmpfile):
            os.remove(tmpfile)

    def split(self, audiofile, segment_time):
        """
        Split audiofile into `segment_time` second size chunks.

        :param audiofile: audiofile to split
        :type audiofile: str
        :param segment_time: desired number of seconds of each chunk
        :type segment_time: int
        """

        import os

        audiofile = os.path.abspath(audiofile)
        cmd = '{} -i "{}" -f segment -segment_time {} -c copy "{}-ffmpeg-%03d{}"'.format(
            self.bin,
            audiofile,
            segment_time,
            os.path.splitext(audiofile)[0],
            os.path.splitext(audiofile)[1])

        self.logger.logvars(locals())

        pydoni.syscmd(cmd)

    def m4a_to_mp3(self, m4a_file):
        """
        Use ffmpeg to convert a .m4a file to .mp3.

        :param m4a_file: path to file to convert to .mp3
        :type m4a_file: str
        """
        import os

        m4a_file = os.path.abspath(m4a_file)
        cmd = '{} -i "{}" -codec:v copy -codec:a libmp3lame -q:a 2 "{}.mp3"'.format(
            self.bin, m4a_file, os.path.splitext(m4a_file)[0])

        self.logger.logvars(locals())

        pydoni.syscmd(cmd)

    def to_gif(self, moviefile, giffile=None, fps=10):
        """
        Convert movie file to gif.

        :param moviefile: path to movie file
        :type moviefile: str
        :param giffile: path to output gif file. If None, then use same name as `moviefile`
                        but substitute extension for '.gif'
        :type giffile: str, None
        :param fps: desired frames per second of output gif
        :type fps: int
        """
        import os

        outfile = giffile if giffile is not None else os.path.splitext(moviefile)[0] + '.gif'
        moviefile = os.path.abspath(moviefile)
        cmd = '{} -i "{}" -r {} "{}"'.format(self.bin, moviefile, str(fps), outfile)

        if os.path.isfile(outfile):
            os.remove(outfile)

        self.logger.logvars(locals())
        pydoni.syscmd(cmd)


class Git(object):
    """
    House git command line function python wrappers.
    """
    import os

    def __init__(self):
        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

    def is_git_repo(self, dir=os.getcwd()):
        """
        Determine whether current dir is a git repository.

        :param dir: directory to check if git repo
        :type dir: str
        :return: True if '.git' found in directory contents, False otherwise
        :rtype: bool
        """
        import os

        self.logger.logvars(locals())

        owd = os.getcwd()
        if dir != owd:
            os.chdir(dir)

        is_repo = True if '.git' in os.listdir() else False
        self.logger.info("'%s' is%s a git repo" % (dir, '' if is_repo else ' not'))

        if dir != owd:
            os.chdir(owd)

        return is_repo

    def status(self, dir=os.getcwd()):
        """
        Return boolean based on output of 'git status' command. Return True if working tree is
        up to date and does not require commit, False if commit is required.

        :return: bool
        """

        import os

        owd = os.getcwd()
        if dir != owd:
            os.chdir(dir)

        self.logger.logvars(locals())

        out = pydoni.syscmd('git status').decode()
        working_tree_clean = "On branch masterYour branch is up to date with 'origin/master'.nothing to commit, working tree clean"
        not_git_repo = 'fatal: not a git repository (or any of the parent directories): .git'

        if dir != owd:
            os.chdir(owd)

        if out.replace('\n', '') == working_tree_clean:
            self.logger.info('Status: Working tree clean')
            return True
        elif out.replace('\n', '') == not_git_repo:
            self.logger.info('Status: Not git repo')
            return None
        else:
            self.logger.info('Status: Commit required')
            return False

    def add(self, fpath=None, all=False):
        """
        Add files to commit.

        :param fpath: file(s) to add
        :type fpath: str, list
        :param all: execute 'git add .'
        :type all: bool
        """
        self.logger.var('fpath', fpath)
        self.logger.var('all', all)

        if all == True and fpath is None:
            pydoni.syscmd('git add .;', encoding='utf-8')
        elif isinstance(fpath, str):
            pydoni.syscmd('git add "%s";' % fpath, encoding='utf-8')
        elif isinstance(fpath, list):
            for f in fpath:
                pydoni.syscmd('git add "%s";' % f, encoding='utf-8')
        else:
            self.logger.error('Nonsensical `fpath` and `all` options! Nothing done.')

    def commit(self, msg):
        """
        Execute 'git commit -m {}' where {} is commit message.

        :param msg: commit message
        :type msg: str
        """
        import subprocess

        self.logger.var('msg', msg)
        cmd = "git commit -m '{}';".format(msg)
        self.logger.var('cmd', cmd)
        subprocess.call(cmd, shell=True)

    def push(self):
        """
        Execute 'git push'.
        """
        import subprocess

        cmd = "git push;"
        self.logger.var('cmd', cmd)
        subprocess.call(cmd, shell=True)

    def pull(self):
        """
        Execute 'git pull'.
        """
        import subprocess

        cmd = "git pull;"
        self.logger.var('cmd', cmd)
        subprocess.call(cmd, shell=True)


class AppleScript(object):
    """
    Store Applescript-wrapper operations.
    """

    def __init__(self):
        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)
        self.logger.logvars(locals())

    def execute(self, applescript):
        """
        Wrapper for pydoni.sh.osascript

        :param applescript:: applescript string to execute
        :type applescript: str
        """

        out = osascript(applescript)
        self.logger.logvars(locals())
        if 'error' in out.lower():
            raise Exception(str(out))

    def new_terminal_tab(self):
        """
        Make new Terminal window.
        """

        applescript = """
        tell application "Terminal"
            activate
            tell application "System Events" to keystroke "t" using command down
            repeat while contents of selected tab of window 1 starts with linefeed
                delay 0.01
            end repeat
        end tell"""

        self.logger.logvars(locals())
        self.execute(applescript)

    def execute_shell_script_in_new_tab(self, shell_script):
        """
        Create a new Terminal tab, then execute given shell scripts.

        :param shell_script: shell script string to execute in default shell
        :type shell_script: str
        """

        applescript = """
        tell application "Terminal"
            activate
            tell application "System Events" to keystroke "t" using command down
            repeat while contents of selected tab of window 1 starts with linefeed
                delay 0.01
            end repeat
            do script "{}" in window 1
        end tell
        """.format(shell_script.replace('"', '\\"'))
        applescript = applescript.replace('\\\\"', '\"')

        self.logger.logvars(locals())

        self.execute(applescript)


def find_binary(bin_name, bin_paths=['/usr/bin', '/usr/local/bin'], abort=False, return_first=False):
    """
    Find system binary by name. If multiple binaries found, return a list of binaries unless
    `return_first` is True, in which case just return the first binary found.

    Ex: find_binary('exiftool') will yield '/usr/local/exiftool' if exiftool installed, and
        it will return None if it's not installed

    :param bin_name: name of binary to search for
    :type bin_name: str
    :param bin_paths: list of paths to search for binary in
    :type bin_paths: list
    :param abort: raise FileNotFoundError if no binary found
    :type abort: bool
    :param return_first: if multiple matches found, return first found binary as string
    :type return_first: str
    :return: absolute path of found binary, else None
    :rtype: str or list if multiple matches found and `return_first` is False
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    assert isinstance(bin_name, str)
    assert isinstance(bin_paths, list)

    owd = os.getcwd()
    logger.var('owd', owd)

    match = []
    for path in bin_paths:
        os.chdir(path)
        binaries = pydoni.listfiles()
        for binary in binaries:
            if bin_name == binary:
                match_item = os.path.join(path, binary)
                match.append(match_item)
                logger.info("Matching binary found %s" % match_item)

    if len(match) > 1:
        if return_first:
            logger.warn("Multiple matches found for `{}`, returning first: {}".format(bin_name, str(match)))
            return match[0]
        else:
            logger.warn("Multiple matches found for `{}`: {}".format(bin_name, str(match)))
            return match

    elif len(match) == 0:
        if abort:
            raise FileNotFoundError("No binaries found for: " + bin_name)
        else:
            logger.warn("No binaries found! Returning None.")
        return None

    os.chdir(owd)
    return match[0]


def adobe_dng_converter(fpath, overwrite=False):
    """
    Run Adobe DNG Converter on a file.

    :param fpath: path to file or files to run Adobe DNG Converter on
    :type fpath: str, list
    :param overwrite: if output file already exists, overwrite it
    :type overwrite: bool
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    # Check if destination file already exists
    # Build output file with .dng extension and check if it exists
    fpath = pydoni.ensurelist(fpath)
    destfile = os.path.join(os.path.splitext(fpath)[0], '.dng')
    exists = True if os.path.isfile(destfile) else False

    logger.logvars(locals())

    # Build system command
    app = os.path.join('/', 'Applications', 'Adobe DNG Converter.app',
        'Contents', 'MacOS', 'Adobe DNG Converter')
    cmd = '"{}" "{}"'.format(app, fpath)

    logger.var('app', app)
    logger.var('cmd', cmd)

    # Execute command if output file does not exist, or if `overwrite` is True
    if exists:
        if overwrite:
            pydoni.syscmd(cmd)
        else:
            # File exists but `overwrite` not specified as True
            pass
    else:
        pydoni.syscmd(cmd)


def stat(fname):
    """
    Call 'stat' UNIX command and parse output into a Python dictionary.

    :param fname: path to file
    :type fname: str
    :returns: dictionary with items:
                File
                Size
                FileType
                Mode
                Uid
                Device
                Inode
                Links
                AccessDate
                ModifyDate
                ChangeDate
    :rtype: dict
    """
    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    def parse_datestring(fname, datestring):
        """
        Extract datestring from `stat` output.

        fname: filename in question
        :type fname: str
            datestring: string containing date
            :type datestring: str
        """
        import os
        from datetime import datetime

        logger.logvars(locals())

        try:
            dt = datetime.strptime(datestring, '%a %b %d %H:%M:%S %Y')
            logger.var('dt', dt)
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        except Exception as e:
            pydoni.vb.echo("Unable to parse date string '{datestring}' for '{fname}' (original date string returned)".format(**locals()),
                warn=True, error_msg=str(e))
            return datestring

    assert os.path.isfile(fname)

    # Get output of `stat` command and clean for python list
    bin_path = pydoni.sh.find_binary('stat')
    cmd = '{bin_name} -x "{fname}"'.format(**locals())
    res = pydoni.syscmd(cmd, encoding='utf-8')
    res = [x.strip() for x in res.split('\n')]

    logger.var('cmd', cmd)
    logger.var('res', res)

    # Tease out each element of `stat` output
    items = ['File', 'Size', 'FileType', 'Mode', 'Uid', 'Device', 'Inode', 'Links',
        'AccessDate', 'ModifyDate', 'ChangeDate']
    logger.var('items', items)

    out = {}
    for item in items:
        try:
            if item == 'File':
                out[item] = res[0].split(':')[1].split('"')[1]
            elif item == 'Size':
                out[item] = res[1].split(':')[1].strip().split(' ')[0]
            elif item == 'FileType':
                out[item] = res[1].split(':')[1].strip().split(' ')[1]
            elif item == 'Mode':
                out[item] = res[2].split(':')[1].strip().split(' ')[0]
            elif item == 'Uid':
                out[item] = res[2].split(':')[2].replace('Gid', '').strip()
            elif item == 'Device':
                out[item] = res[3].split(':')[1].replace('Inode', '').strip()
            elif item == 'Inode':
                out[item] = res[3].split(':')[2].replace('Links', '').strip()
            elif item == 'Links':
                out[item] = res[3].split(':')[3].strip()
            elif item == 'AccessDate' :
                out[item] = parse_datestring(fname, res[4].replace('Access:', '').strip())
            elif item == 'ModifyDate' :
                out[item] = parse_datestring(fname, res[5].replace('Modify:', '').strip())
            elif item == 'ChangeDate' :
                out[item] = parse_datestring(fname, res[6].replace('Change:', '').strip())

        except Exception as e:
            out[item] = '<pydoni.sh.stat() ERROR: %s>' % str(e)
            logger.exception("Error extracting key '%s' from stat output. Error message:" % item)
            logger.debug(str(e))

    return out


def mid3v2(fpath, attr_name, attr_value):
    """
    Use mid3v2 to add or overwrite a metadata attribute to a file.

    :param fpath: path to file
    :type fpath: str
    :param attr_name: name of attribute to assign value to using mid3v2, one of
                      ['artist', 'album', 'song', 'comment', 'picture', 'genre',
                      'year', 'date', 'track']
    :type attr_name: str
    :param attr_value: value to assign to attribute `attr_name`
    :type attr_value: str, int
    :return: boolean indicator of successful run
    :rtype: bool
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    valid = ['artist', 'album', 'song', 'comment', 'picture', 'genre', 'year', 'date', 'track']
    logger.var('valid', valid)
    assert attr_name in valid

    bin = pydoni.sh.find_binary('mid3v2')
    logger.var('bin', bin)

    cmd = '{} --{}="{}" "{}"'.format(bin, attr_name, attr_value, fpath)
    logger.var('cmd', cmd)
    pydoni.syscmd(cmd)


def convert_audible(fpath, fmt, activation_bytes):
    """
    Convert Audible .aax file to .mp4.

    :param fpath: path to .aax file
    :type fpath: str
    :param fmt: one of 'mp3' or 'mp4', if 'mp4' then convert output file to mp3
    :type fmt: str
    :param activation_bytes: activation bytes string.
                             See https://github.com/inAudible-NG/audible-activator to get
                             activation byte string
    :type activation_bytes: str
    """
    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    assert os.path.isfile(fpath)
    assert os.path.splitext(fpath)[1].lower() == '.aax'

    # Get output format
    fmt = fmt.lower().replace('.', '')
    assert fmt in ['mp3', 'mp4']

    # Get outfile
    outfile = os.path.splitext(fpath)[0] + '.mp4'
    logger.var('outfile', outfile)
    assert not os.path.isfile(outfile)

    # player_id = '2jmj7l5rSw0yVb/vlWAYkK/YBwk='
    # activation_bytes = '8a87c903'

    # Convert to mp4 (regardless of `fmt` parameter)
    bin = pydoni.sh.find_binary('ffmpeg')
    cmd = '{} -activation_bytes {} -i "{}" -vn -c:a copy "{}"'.format(
        bin, activation_bytes, fpath, outfile)
    logger.var('cmd', cmd)
    pydoni.syscmd(cmd)

    # Convert to mp3 if specified
    if fmt == 'mp3':
        logger.info('Converting MP4 to MP3 at 256k: ' + outfile)
        mp4_to_mp3(outfile, bitrate=256)


def mp4_to_mp3(fpath, bitrate):
    """
    Convert an .mp4 file to a .mp3 file.

    :param fpath: path to .mp4 file
    :type fpath: str
    :param bitrate: bitrate to export as, may also be as string for example '192k'
    :type bitrate: int
    """
    import os, re

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    assert os.path.splitext(fpath)[1].lower() == '.mp4'

    # Get bitrate as string ###k where ### is any number
    bitrate = str(bitrate).replace('k', '') + 'k'
    logger.var('bitrate', bitrate)
    assert re.match(r'\d+k', bitrate)

    # Execute command
    cmd = 'f="{}";ffmpeg -i "$f" -acodec libmp3lame -ab {} "${{f%.mp4}}.mp3";'.format(fpath, bitrate)
    logger.var('cmd', cmd)
    pydoni.syscmd(cmd)


def split_video_scenes(vfpath, outdname):
    """
    Split video using PySceneDetect.

    :param vfpath: path to video file to split
    :type vfpath: str
    :param outdname: path to directory to output clips to
    :type outdname: str
    :return: True if run successfully, False if run unsuccessfully
    :rtype: bool
    """
    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    assert os.path.isfile(vfpath)
    assert os.path.isdir(outdname)

    bin_path = pydoni.sh.find_binary('scenedetect')
    cmd = '{bin_name} --input "{vpath}" --output "{outdname}" detect-content split-video'.format(**locals())
    logger.var('cmd', cmd)

    try:
        pydoni.syscmd(cmd)
        return True
    except Exception as e:
        logger.exception('Failed to split video scenes')
        logger.debug(str(e))
        return False


def osascript(applescript):
    """
    Execute applescript.

    :param applescript: applescript string to execute
    :type applescript: str
    :return: output string from AppleScript command
    :rtype: str
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    bin_name = pydoni.sh.find_binary('osascript')
    applescript = applescript.replace("'", "\'")

    cmd = "{bin_name} -e '{applescript}'".format(**locals())
    out = pydoni.syscmd(cmd)

    if isinstance(out, bytes):
        out = out.decode('utf-8')

    logger.logvars(locals())

    return out
