/**
 * Split NAL units from an H.264/H.265 Annex B stream.
 *
 * The input is not modified.
 * The returned NAL units are views of the input (no memory allocation nor copy),
 * and still contains emulation prevention bytes.
 *
 * This methods returns a generator, so it can be stopped immediately
 * after the interested NAL unit is found.
 */
export function* annexBSplitNalu(buffer) {
    // -1 means we haven't found the first start code
    let start = -1;
    // How many `0x00`s in a row we have counted
    let zeroCount = 0;
    let inEmulation = false;
    for (let i = 0; i < buffer.length; i += 1) {
        const byte = buffer[i];
        if (inEmulation) {
            if (byte > 0x03) {
                // `0x00000304` or larger are invalid
                throw new Error("Invalid data");
            }
            inEmulation = false;
            continue;
        }
        if (byte === 0x00) {
            zeroCount += 1;
            continue;
        }
        const prevZeroCount = zeroCount;
        zeroCount = 0;
        if (start === -1) {
            // 0x000001 is the start code
            // But it can be preceded by any number of zeros
            // So 2 is the minimal
            if (prevZeroCount >= 2 && byte === 0x01) {
                // Found start of first NAL unit
                start = i + 1;
                continue;
            }
            // Not begin with start code
            throw new Error("Invalid data");
        }
        if (prevZeroCount < 2) {
            // zero or one `0x00`s are acceptable
            continue;
        }
        if (byte === 0x01) {
            // Found another NAL unit
            yield buffer.subarray(start, i - prevZeroCount);
            start = i + 1;
            continue;
        }
        if (prevZeroCount > 2) {
            // Too much `0x00`s
            throw new Error("Invalid data");
        }
        switch (byte) {
            case 0x02:
                // Didn't find why, but 7.4.1 NAL unit semantics forbids `0x000002` appearing in NAL units
                throw new Error("Invalid data");
            case 0x03:
                // `0x000003` is the "emulation_prevention_three_byte"
                // `0x00000300`, `0x00000301`, `0x00000302` and `0x00000303` represent
                // `0x000000`, `0x000001`, `0x000002` and `0x000003` respectively
                inEmulation = true;
                break;
            default:
                // `0x000004` or larger are as-is
                break;
        }
    }
    if (inEmulation) {
        throw new Error("Invalid data");
    }
    yield buffer.subarray(start, buffer.length);
}
/**
 * Remove emulation prevention bytes from a H.264/H.265 NAL Unit.
 *
 * The input is not modified.
 * If the input doesn't contain any emulation prevention bytes,
 * the input is returned as-is.
 * Otherwise, a new `Uint8Array` is created and returned.
 */
export function naluRemoveEmulation(buffer) {
    // output will be created when first emulation prevention byte is found
    let output;
    let outputOffset = 0;
    let zeroCount = 0;
    let inEmulation = false;
    let i = 0;
    scan: for (; i < buffer.length; i += 1) {
        const byte = buffer[i];
        if (byte === 0x00) {
            zeroCount += 1;
            continue;
        }
        // Current byte is not zero
        const prevZeroCount = zeroCount;
        zeroCount = 0;
        if (prevZeroCount < 2) {
            // zero or one `0x00`s are acceptable
            continue;
        }
        if (byte === 0x01) {
            // Unexpected start code
            throw new Error("Invalid data");
        }
        if (prevZeroCount > 2) {
            // Too much `0x00`s
            throw new Error("Invalid data");
        }
        switch (byte) {
            case 0x02:
                // Didn't find why, but 7.4.1 NAL unit semantics forbids `0x000002` appearing in NAL units
                throw new Error("Invalid data");
            case 0x03:
                // `0x000003` is the "emulation_prevention_three_byte"
                // `0x00000300`, `0x00000301`, `0x00000302` and `0x00000303` represent
                // `0x000000`, `0x000001`, `0x000002` and `0x000003` respectively
                inEmulation = true;
                // Create output and copy the data before the emulation prevention byte
                // Output size is unknown, so we use the input size as an upper bound
                output = new Uint8Array(buffer.length - 1);
                output.set(buffer.subarray(0, i));
                outputOffset = i;
                i += 1;
                break scan;
            default:
                // `0x000004` or larger are as-is
                break;
        }
    }
    if (!output) {
        return buffer;
    }
    // Continue at the byte after the emulation prevention byte
    for (; i < buffer.length; i += 1) {
        const byte = buffer[i];
        output[outputOffset] = byte;
        outputOffset += 1;
        if (inEmulation) {
            if (byte > 0x03) {
                // `0x00000304` or larger are invalid
                throw new Error("Invalid data");
            }
            // `00000300000300` results in `0000000000` (both `0x03` are removed)
            // which means the `0x00` after `0x03` also counts
            if (byte === 0x00) {
                zeroCount += 1;
            }
            inEmulation = false;
            continue;
        }
        if (byte === 0x00) {
            zeroCount += 1;
            continue;
        }
        const prevZeroCount = zeroCount;
        zeroCount = 0;
        if (prevZeroCount < 2) {
            // zero or one `0x00`s are acceptable
            continue;
        }
        if (byte === 0x01) {
            // Unexpected start code
            throw new Error("Invalid data");
        }
        if (prevZeroCount > 2) {
            // Too much `0x00`s
            throw new Error("Invalid data");
        }
        switch (byte) {
            case 0x02:
                // Didn't find why, but 7.4.1 NAL unit semantics forbids `0x000002` appearing in NAL units
                throw new Error("Invalid data");
            case 0x03:
                // `0x000003` is the "emulation_prevention_three_byte"
                // `0x00000300`, `0x00000301`, `0x00000302` and `0x00000303` represent
                // `0x000000`, `0x000001`, `0x000002` and `0x000003` respectively
                inEmulation = true;
                // Remove the emulation prevention byte
                outputOffset -= 1;
                break;
            default:
                // `0x000004` or larger are as-is
                break;
        }
    }
    return output.subarray(0, outputOffset);
}
export class NaluSodbBitReader {
    get byteLength() {
        return this._byteLength;
    }
    get stopBitIndex() {
        return this._stopBitIndex;
    }
    get bytePosition() {
        return this._bytePosition;
    }
    get bitPosition() {
        return this._bitPosition;
    }
    get ended() {
        return (this._bytePosition === this._byteLength &&
            this._bitPosition === this._stopBitIndex);
    }
    constructor(nalu) {
        this._zeroCount = 0;
        this._bytePosition = -1;
        this._bitPosition = -1;
        this._byte = 0;
        this._nalu = nalu;
        for (let i = nalu.length - 1; i >= 0; i -= 1) {
            if (this._nalu[i] === 0) {
                continue;
            }
            const byte = nalu[i];
            for (let j = 0; j < 8; j += 1) {
                if (((byte >> j) & 1) === 1) {
                    this._byteLength = i;
                    this._stopBitIndex = j;
                    this.readByte();
                    return;
                }
            }
        }
        throw new Error("End bit not found");
    }
    readByte() {
        this._byte = this._nalu[this._bytePosition];
        if (this._zeroCount === 2 && this._byte === 3) {
            this._zeroCount = 0;
            this._bytePosition += 1;
            this.readByte();
            return;
        }
        if (this._byte === 0) {
            this._zeroCount += 1;
        }
        else {
            this._zeroCount = 0;
        }
    }
    next() {
        if (this._bitPosition === -1) {
            this._bitPosition = 7;
            this._bytePosition += 1;
            this.readByte();
        }
        if (this._bytePosition === this._byteLength &&
            this._bitPosition === this._stopBitIndex) {
            throw new Error("Bit index out of bounds");
        }
        const value = (this._byte >> this._bitPosition) & 1;
        this._bitPosition -= 1;
        return value;
    }
    read(length) {
        if (length > 32) {
            throw new Error("Read length too large");
        }
        let result = 0;
        for (let i = 0; i < length; i += 1) {
            result = (result << 1) | this.next();
        }
        return result;
    }
    skip(length) {
        for (let i = 0; i < length; i += 1) {
            this.next();
        }
    }
    decodeExponentialGolombNumber() {
        let length = 0;
        while (this.next() === 0) {
            length += 1;
        }
        if (length === 0) {
            return 0;
        }
        return ((1 << length) | this.read(length)) - 1;
    }
    peek(length) {
        const { _zeroCount, _bytePosition, _bitPosition, _byte } = this;
        const result = this.read(length);
        Object.assign(this, { _zeroCount, _bytePosition, _bitPosition, _byte });
        return result;
    }
    readBytes(length) {
        const result = new Uint8Array(length);
        for (let i = 0; i < length; i += 1) {
            result[i] = this.read(8);
        }
        return result;
    }
    peekBytes(length) {
        const { _zeroCount, _bytePosition, _bitPosition, _byte } = this;
        const result = this.readBytes(length);
        Object.assign(this, { _zeroCount, _bytePosition, _bitPosition, _byte });
        return result;
    }
}
export var AndroidHevcProfile;
(function (AndroidHevcProfile) {
    AndroidHevcProfile[AndroidHevcProfile["Main"] = 1] = "Main";
    AndroidHevcProfile[AndroidHevcProfile["Main10"] = 2] = "Main10";
    AndroidHevcProfile[AndroidHevcProfile["MainStill"] = 4] = "MainStill";
    AndroidHevcProfile[AndroidHevcProfile["Main10Hdr10"] = 4096] = "Main10Hdr10";
    AndroidHevcProfile[AndroidHevcProfile["Main10Hdr10Plus"] = 8192] = "Main10Hdr10Plus";
})(AndroidHevcProfile || (AndroidHevcProfile = {}));
export var AndroidHevcLevel;
(function (AndroidHevcLevel) {
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel1"] = 1] = "MainTierLevel1";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel1"] = 2] = "HighTierLevel1";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel2"] = 4] = "MainTierLevel2";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel2"] = 8] = "HighTierLevel2";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel21"] = 16] = "MainTierLevel21";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel21"] = 32] = "HighTierLevel21";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel3"] = 64] = "MainTierLevel3";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel3"] = 128] = "HighTierLevel3";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel31"] = 256] = "MainTierLevel31";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel31"] = 512] = "HighTierLevel31";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel4"] = 1024] = "MainTierLevel4";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel4"] = 2048] = "HighTierLevel4";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel41"] = 4096] = "MainTierLevel41";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel41"] = 8192] = "HighTierLevel41";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel5"] = 16384] = "MainTierLevel5";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel5"] = 32768] = "HighTierLevel5";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel51"] = 65536] = "MainTierLevel51";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel51"] = 131072] = "HighTierLevel51";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel52"] = 262144] = "MainTierLevel52";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel52"] = 524288] = "HighTierLevel52";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel6"] = 1048576] = "MainTierLevel6";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel6"] = 2097152] = "HighTierLevel6";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel61"] = 4194304] = "MainTierLevel61";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel61"] = 8388608] = "HighTierLevel61";
    AndroidHevcLevel[AndroidHevcLevel["MainTierLevel62"] = 16777216] = "MainTierLevel62";
    AndroidHevcLevel[AndroidHevcLevel["HighTierLevel62"] = 33554432] = "HighTierLevel62";
})(AndroidHevcLevel || (AndroidHevcLevel = {}));
/**
 * 6.2 Source, decoded and output picture formats
 */
export function getSubWidthC(chroma_format_idc) {
    switch (chroma_format_idc) {
        case 0:
        case 3:
            return 1;
        case 1:
        case 2:
            return 2;
        default:
            throw new Error("Invalid chroma_format_idc");
    }
}
/**
 * 6.2 Source, decoded and output picture formats
 */
export function getSubHeightC(chroma_format_idc) {
    switch (chroma_format_idc) {
        case 0:
        case 2:
        case 3:
            return 1;
        case 1:
            return 2;
        default:
            throw new Error("Invalid chroma_format_idc");
    }
}
/**
 * 7.3.1.1 General NAL unit syntax
 */
export function h265ParseNaluHeader(nalu) {
    const reader = new NaluSodbBitReader(nalu);
    if (reader.next() !== 0) {
        throw new Error("Invalid NALU header");
    }
    const nal_unit_type = reader.read(6);
    const nuh_layer_id = reader.read(6);
    const nuh_temporal_id_plus1 = reader.read(3);
    return {
        nal_unit_type,
        nuh_layer_id,
        nuh_temporal_id_plus1,
    };
}
/**
 * 7.3.2.1 Video parameter set RBSP syntax
 */
export function h265ParseVideoParameterSet(nalu) {
    const reader = new NaluSodbBitReader(nalu);
    const vps_video_parameter_set_id = reader.read(4);
    const vps_base_layer_internal_flag = !!reader.next();
    const vps_base_layer_available_flag = !!reader.next();
    const vps_max_layers_minus1 = reader.read(6);
    const vps_max_sub_layers_minus1 = reader.read(3);
    const vps_temporal_id_nesting_flag = !!reader.next();
    reader.skip(16);
    const profileTierLevel = h265ParseProfileTierLevel(reader, true, vps_max_sub_layers_minus1);
    const vps_sub_layer_ordering_info_present_flag = !!reader.next();
    const vps_max_dec_pic_buffering_minus1 = [];
    const vps_max_num_reorder_pics = [];
    const vps_max_latency_increase_plus1 = [];
    for (let i = vps_sub_layer_ordering_info_present_flag
        ? 0
        : vps_max_sub_layers_minus1; i <= vps_max_sub_layers_minus1; i += 1) {
        vps_max_dec_pic_buffering_minus1[i] =
            reader.decodeExponentialGolombNumber();
        vps_max_num_reorder_pics[i] = reader.decodeExponentialGolombNumber();
        vps_max_latency_increase_plus1[i] =
            reader.decodeExponentialGolombNumber();
    }
    const vps_max_layer_id = reader.read(6);
    const vps_num_layer_sets_minus1 = reader.decodeExponentialGolombNumber();
    const layer_id_included_flag = [];
    for (let i = 1; i <= vps_num_layer_sets_minus1; i += 1) {
        layer_id_included_flag[i] = [];
        for (let j = 0; j <= vps_max_layer_id; j += 1) {
            layer_id_included_flag[i][j] = !!reader.next();
        }
    }
    const vps_timing_info_present_flag = !!reader.next();
    let vps_num_units_in_tick;
    let vps_time_scale;
    let vps_poc_proportional_to_timing_flag;
    let vps_num_ticks_poc_diff_one_minus1;
    let vps_num_hrd_parameters;
    let hrd_layer_set_idx;
    let cprms_present_flag;
    let hrdParameters;
    if (vps_timing_info_present_flag) {
        vps_num_units_in_tick = reader.read(32);
        vps_time_scale = reader.read(32);
        vps_poc_proportional_to_timing_flag = !!reader.next();
        if (vps_poc_proportional_to_timing_flag) {
            vps_num_ticks_poc_diff_one_minus1 =
                reader.decodeExponentialGolombNumber();
        }
        vps_num_hrd_parameters = reader.decodeExponentialGolombNumber();
        hrd_layer_set_idx = [];
        cprms_present_flag = [true];
        hrdParameters = [];
        for (let i = 0; i < vps_num_hrd_parameters; i += 1) {
            hrd_layer_set_idx[i] = reader.decodeExponentialGolombNumber();
            if (i > 0) {
                cprms_present_flag[i] = !!reader.next();
            }
            hrdParameters[i] = h265ParseHrdParameters(reader, cprms_present_flag[i], vps_max_sub_layers_minus1);
        }
    }
    const vps_extension_flag = !!reader.next();
    return {
        vps_video_parameter_set_id,
        vps_base_layer_internal_flag,
        vps_base_layer_available_flag,
        vps_max_layers_minus1,
        vps_max_sub_layers_minus1,
        vps_temporal_id_nesting_flag,
        profileTierLevel,
        vps_sub_layer_ordering_info_present_flag,
        vps_max_dec_pic_buffering_minus1,
        vps_max_num_reorder_pics,
        vps_max_latency_increase_plus1,
        vps_max_layer_id,
        vps_num_layer_sets_minus1,
        layer_id_included_flag,
        vps_timing_info_present_flag,
        vps_num_units_in_tick,
        vps_time_scale,
        vps_poc_proportional_to_timing_flag,
        vps_num_ticks_poc_diff_one_minus1,
        vps_num_hrd_parameters,
        hrd_layer_set_idx,
        cprms_present_flag,
        hrdParameters,
        vps_extension_flag,
    };
}
/**
 * 7.3.2.2.1 General sequence parameter set RBSP syntax
 */
export function h265ParseSequenceParameterSet(nalu) {
    const reader = new NaluSodbBitReader(nalu);
    const sps_video_parameter_set_id = reader.read(4);
    const sps_max_sub_layers_minus1 = reader.read(3);
    const sps_temporal_id_nesting_flag = !!reader.next();
    const profileTierLevel = h265ParseProfileTierLevel(reader, true, sps_max_sub_layers_minus1);
    const sps_seq_parameter_set_id = reader.decodeExponentialGolombNumber();
    const chroma_format_idc = reader.decodeExponentialGolombNumber();
    let separate_colour_plane_flag;
    if (chroma_format_idc === 3) {
        separate_colour_plane_flag = !!reader.next();
    }
    const pic_width_in_luma_samples = reader.decodeExponentialGolombNumber();
    const pic_height_in_luma_samples = reader.decodeExponentialGolombNumber();
    const conformance_window_flag = !!reader.next();
    let conf_win_left_offset;
    let conf_win_right_offset;
    let conf_win_top_offset;
    let conf_win_bottom_offset;
    if (conformance_window_flag) {
        conf_win_left_offset = reader.decodeExponentialGolombNumber();
        conf_win_right_offset = reader.decodeExponentialGolombNumber();
        conf_win_top_offset = reader.decodeExponentialGolombNumber();
        conf_win_bottom_offset = reader.decodeExponentialGolombNumber();
    }
    const bit_depth_luma_minus8 = reader.decodeExponentialGolombNumber();
    const bit_depth_chroma_minus8 = reader.decodeExponentialGolombNumber();
    const log2_max_pic_order_cnt_lsb_minus4 = reader.decodeExponentialGolombNumber();
    let sps_max_dec_pic_buffering_minus1;
    let sps_max_num_reorder_pics;
    let sps_max_latency_increase_plus1;
    const sps_sub_layer_ordering_info_present_flag = !!reader.next();
    for (let i = sps_sub_layer_ordering_info_present_flag
        ? 0
        : sps_max_sub_layers_minus1; i <= sps_max_sub_layers_minus1; i += 1) {
        sps_max_dec_pic_buffering_minus1 = [];
        sps_max_num_reorder_pics = [];
        sps_max_latency_increase_plus1 = [];
        for (let i = 0; i <= sps_max_sub_layers_minus1; i += 1) {
            sps_max_dec_pic_buffering_minus1[i] =
                reader.decodeExponentialGolombNumber();
            sps_max_num_reorder_pics[i] =
                reader.decodeExponentialGolombNumber();
            sps_max_latency_increase_plus1[i] =
                reader.decodeExponentialGolombNumber();
        }
    }
    const log2_min_luma_coding_block_size_minus3 = reader.decodeExponentialGolombNumber();
    const log2_diff_max_min_luma_coding_block_size = reader.decodeExponentialGolombNumber();
    const log2_min_luma_transform_block_size_minus2 = reader.decodeExponentialGolombNumber();
    const log2_diff_max_min_luma_transform_block_size = reader.decodeExponentialGolombNumber();
    const max_transform_hierarchy_depth_inter = reader.decodeExponentialGolombNumber();
    const max_transform_hierarchy_depth_intra = reader.decodeExponentialGolombNumber();
    const scaling_list_enabled_flag = !!reader.next();
    let sps_scaling_list_data_present_flag;
    let scalingListData;
    if (scaling_list_enabled_flag) {
        sps_scaling_list_data_present_flag = !!reader.next();
        if (sps_scaling_list_data_present_flag) {
            scalingListData = h265ParseScalingListData(reader);
        }
    }
    const amp_enabled_flag = !!reader.next();
    const sample_adaptive_offset_enabled_flag = !!reader.next();
    const pcm_enabled_flag = !!reader.next();
    let pcm_sample_bit_depth_luma_minus1;
    let pcm_sample_bit_depth_chroma_minus1;
    let log2_min_pcm_luma_coding_block_size_minus3;
    let log2_diff_max_min_pcm_luma_coding_block_size;
    let pcm_loop_filter_disabled_flag;
    if (pcm_enabled_flag) {
        pcm_sample_bit_depth_luma_minus1 = reader.read(4);
        pcm_sample_bit_depth_chroma_minus1 = reader.read(4);
        log2_min_pcm_luma_coding_block_size_minus3 = reader.read(4);
        log2_diff_max_min_pcm_luma_coding_block_size = reader.read(4);
        pcm_loop_filter_disabled_flag = !!reader.next();
    }
    const num_short_term_ref_pic_sets = reader.decodeExponentialGolombNumber();
    const shortTermRefPicSets = [];
    for (let i = 0; i < num_short_term_ref_pic_sets; i += 1) {
        shortTermRefPicSets[i] = h265ParseShortTermReferencePictureSet(reader, i, num_short_term_ref_pic_sets, shortTermRefPicSets);
    }
    const long_term_ref_pics_present_flag = !!reader.next();
    let num_long_term_ref_pics_sps;
    let lt_ref_pic_poc_lsb_sps;
    let used_by_curr_pic_lt_sps_flag;
    if (long_term_ref_pics_present_flag) {
        num_long_term_ref_pics_sps = reader.decodeExponentialGolombNumber();
        lt_ref_pic_poc_lsb_sps = [];
        used_by_curr_pic_lt_sps_flag = [];
        for (let i = 0; i < num_long_term_ref_pics_sps; i += 1) {
            lt_ref_pic_poc_lsb_sps[i] = reader.read(log2_max_pic_order_cnt_lsb_minus4 + 4);
            used_by_curr_pic_lt_sps_flag[i] = !!reader.next();
        }
    }
    const sps_temporal_mvp_enabled_flag = !!reader.next();
    const strong_intra_smoothing_enabled_flag = !!reader.next();
    const vui_parameters_present_flag = !!reader.next();
    let vuiParameters;
    if (vui_parameters_present_flag) {
        vuiParameters = h265ParseVuiParameters(reader);
    }
    const sps_extension_present_flag = !!reader.next();
    let sps_range_extension_flag;
    let sps_multilayer_extension_flag;
    let sps_3d_extension_flag;
    let sps_scc_extension_flag;
    let sps_extension_4bits;
    if (sps_extension_present_flag) {
        sps_range_extension_flag = !!reader.next();
        sps_multilayer_extension_flag = !!reader.next();
        sps_3d_extension_flag = !!reader.next();
        sps_scc_extension_flag = !!reader.next();
        sps_extension_4bits = reader.read(4);
    }
    if (sps_range_extension_flag) {
        throw new Error("Not implemented");
    }
    let spsMultilayerExtension;
    if (sps_multilayer_extension_flag) {
        spsMultilayerExtension = h265ParseSpsMultilayerExtension(reader);
    }
    let sps3dExtension;
    if (sps_3d_extension_flag) {
        sps3dExtension = h265ParseSps3dExtension(reader);
    }
    if (sps_scc_extension_flag) {
        throw new Error("Not implemented");
    }
    let sps_extension_data_flag;
    if (sps_extension_4bits) {
        sps_extension_data_flag = [];
        let i = 0;
        while (!reader.ended) {
            sps_extension_data_flag[i] = !!reader.next();
            i += 1;
        }
    }
    return {
        sps_video_parameter_set_id,
        sps_max_sub_layers_minus1,
        sps_temporal_id_nesting_flag,
        profileTierLevel,
        sps_seq_parameter_set_id,
        chroma_format_idc,
        separate_colour_plane_flag,
        pic_width_in_luma_samples,
        pic_height_in_luma_samples,
        conformance_window_flag,
        conf_win_left_offset,
        conf_win_right_offset,
        conf_win_top_offset,
        conf_win_bottom_offset,
        bit_depth_luma_minus8,
        bit_depth_chroma_minus8,
        log2_max_pic_order_cnt_lsb_minus4,
        sps_sub_layer_ordering_info_present_flag,
        sps_max_dec_pic_buffering_minus1,
        sps_max_num_reorder_pics,
        sps_max_latency_increase_plus1,
        log2_min_luma_coding_block_size_minus3,
        log2_diff_max_min_luma_coding_block_size,
        log2_min_luma_transform_block_size_minus2,
        log2_diff_max_min_luma_transform_block_size,
        max_transform_hierarchy_depth_inter,
        max_transform_hierarchy_depth_intra,
        scaling_list_enabled_flag,
        sps_scaling_list_data_present_flag,
        scalingListData,
        amp_enabled_flag,
        sample_adaptive_offset_enabled_flag,
        pcm_enabled_flag,
        pcm_sample_bit_depth_luma_minus1,
        pcm_sample_bit_depth_chroma_minus1,
        log2_min_pcm_luma_coding_block_size_minus3,
        log2_diff_max_min_pcm_luma_coding_block_size,
        pcm_loop_filter_disabled_flag,
        num_short_term_ref_pic_sets,
        shortTermRefPicSets,
        long_term_ref_pics_present_flag,
        num_long_term_ref_pics_sps,
        lt_ref_pic_poc_lsb_sps,
        used_by_curr_pic_lt_sps_flag,
        sps_temporal_mvp_enabled_flag,
        strong_intra_smoothing_enabled_flag,
        vui_parameters_present_flag,
        vuiParameters,
        sps_extension_present_flag,
        sps_range_extension_flag,
        sps_multilayer_extension_flag,
        sps_3d_extension_flag,
        sps_scc_extension_flag,
        sps_extension_4bits,
        spsMultilayerExtension,
        sps3dExtension,
        sps_extension_data_flag,
    };
}
/**
 * 7.3.3 Profile, tier and level syntax
 *
 * Common part between general_profile_tier_level and
 * sub_layer_profile_tier_level
 */
function h265ParseProfileTier(reader) {
    const profile_space = reader.read(2);
    const tier_flag = !!reader.next();
    const profile_idc = reader.read(5);
    const profileCompatibilitySet = reader.peekBytes(4);
    const profile_compatibility_flag = [];
    for (let j = 0; j < 32; j += 1) {
        profile_compatibility_flag[j] = !!reader.next();
    }
    const constraintSet = reader.peekBytes(6);
    const progressive_source_flag = !!reader.next();
    const interlaced_source_flag = !!reader.next();
    const non_packed_constraint_flag = !!reader.next();
    const frame_only_constraint_flag = !!reader.next();
    let max_12bit_constraint_flag;
    let max_10bit_constraint_flag;
    let max_8bit_constraint_flag;
    let max_422chroma_constraint_flag;
    let max_420chroma_constraint_flag;
    let max_monochrome_constraint_flag;
    let intra_constraint_flag;
    let one_picture_only_constraint_flag;
    let lower_bit_rate_constraint_flag;
    let max_14bit_constraint_flag;
    if (profile_idc === 4 ||
        profile_compatibility_flag[4] ||
        profile_idc === 5 ||
        profile_compatibility_flag[5] ||
        profile_idc === 6 ||
        profile_compatibility_flag[6] ||
        profile_idc === 7 ||
        profile_compatibility_flag[7] ||
        profile_idc === 8 ||
        profile_compatibility_flag[8] ||
        profile_idc === 9 ||
        profile_compatibility_flag[9] ||
        profile_idc === 10 ||
        profile_compatibility_flag[10] ||
        profile_idc === 11 ||
        profile_compatibility_flag[11]) {
        max_12bit_constraint_flag = !!reader.next();
        max_10bit_constraint_flag = !!reader.next();
        max_8bit_constraint_flag = !!reader.next();
        max_422chroma_constraint_flag = !!reader.next();
        max_420chroma_constraint_flag = !!reader.next();
        max_monochrome_constraint_flag = !!reader.next();
        intra_constraint_flag = !!reader.next();
        one_picture_only_constraint_flag = !!reader.next();
        lower_bit_rate_constraint_flag = !!reader.next();
        if (profile_idc === 5 ||
            profile_compatibility_flag[5] ||
            profile_idc === 9 ||
            profile_compatibility_flag[9] ||
            profile_idc === 10 ||
            profile_compatibility_flag[10] ||
            profile_idc === 11 ||
            profile_compatibility_flag[11]) {
            max_14bit_constraint_flag = !!reader.next();
            reader.skip(33);
        }
        else {
            reader.skip(34);
        }
    }
    else if (profile_idc === 2 || profile_compatibility_flag[2]) {
        reader.skip(7);
        one_picture_only_constraint_flag = !!reader.next();
        reader.skip(35);
    }
    else {
        reader.skip(43);
    }
    let inbld_flag;
    if (profile_idc === 1 ||
        profile_compatibility_flag[1] ||
        profile_idc === 2 ||
        profile_compatibility_flag[2] ||
        profile_idc === 3 ||
        profile_compatibility_flag[3] ||
        profile_idc === 4 ||
        profile_compatibility_flag[4] ||
        profile_idc === 5 ||
        profile_compatibility_flag[5] ||
        profile_idc === 9 ||
        profile_compatibility_flag[9] ||
        profile_idc === 11 ||
        profile_compatibility_flag[11]) {
        inbld_flag = !!reader.next();
    }
    else {
        reader.skip(1);
    }
    return {
        profile_space,
        tier_flag,
        profile_idc,
        profileCompatibilitySet,
        profile_compatibility_flag,
        constraintSet,
        progressive_source_flag,
        interlaced_source_flag,
        non_packed_constraint_flag,
        frame_only_constraint_flag,
        max_12bit_constraint_flag,
        max_10bit_constraint_flag,
        max_8bit_constraint_flag,
        max_422chroma_constraint_flag,
        max_420chroma_constraint_flag,
        max_monochrome_constraint_flag,
        intra_constraint_flag,
        one_picture_only_constraint_flag,
        lower_bit_rate_constraint_flag,
        max_14bit_constraint_flag,
        inbld_flag,
    };
}
function h265ParseProfileTierLevel(reader, profilePresentFlag, maxNumSubLayersMinus1) {
    let generalProfileTier;
    if (profilePresentFlag) {
        generalProfileTier = h265ParseProfileTier(reader);
    }
    const general_level_idc = reader.read(8);
    const sub_layer_profile_present_flag = [];
    const sub_layer_level_present_flag = [];
    for (let i = 0; i < maxNumSubLayersMinus1; i += 1) {
        sub_layer_profile_present_flag[i] = !!reader.next();
        sub_layer_level_present_flag[i] = !!reader.next();
    }
    if (maxNumSubLayersMinus1 > 0) {
        for (let i = maxNumSubLayersMinus1; i < 8; i += 1) {
            reader.read(2);
        }
    }
    const subLayerProfileTier = [];
    const sub_layer_level_idc = [];
    for (let i = 0; i < maxNumSubLayersMinus1; i += 1) {
        if (sub_layer_profile_present_flag[i]) {
            subLayerProfileTier[i] = h265ParseProfileTier(reader);
        }
        if (sub_layer_level_present_flag[i]) {
            sub_layer_level_idc[i] = reader.read(8);
        }
    }
    return {
        generalProfileTier,
        general_level_idc,
        sub_layer_profile_present_flag,
        sub_layer_level_present_flag,
        subLayerProfileTier,
        sub_layer_level_idc,
    };
}
/**
 * 7.3.4 Scaling list data syntax
 */
export function h265ParseScalingListData(reader) {
    const scaling_list = [];
    for (let sizeId = 0; sizeId < 4; sizeId += 1) {
        scaling_list[sizeId] = [];
        for (let matrixId = 0; matrixId < 6; matrixId += sizeId === 3 ? 3 : 1) {
            const scaling_list_pred_mode_flag = !!reader.next();
            if (!scaling_list_pred_mode_flag) {
                reader.decodeExponentialGolombNumber();
            }
            else {
                let nextCoef = 8;
                const coefNum = Math.min(64, 1 << (4 + (sizeId << 1)));
                if (sizeId > 1) {
                    const scaling_list_dc_coef_minus8 = reader.decodeExponentialGolombNumber();
                    nextCoef = scaling_list_dc_coef_minus8 + 8;
                }
                scaling_list[sizeId][matrixId] = [];
                for (let i = 0; i < coefNum; i += 1) {
                    const scaling_list_delta_coef = reader.decodeExponentialGolombNumber();
                    nextCoef = (nextCoef + scaling_list_delta_coef + 256) % 256;
                    scaling_list[sizeId][matrixId][i] = nextCoef;
                }
            }
        }
    }
    return scaling_list;
}
/**
 * 7.3.7 Short-term reference picture set syntax
 */
export function h265ParseShortTermReferencePictureSet(reader, stRpsIdx, num_short_term_ref_pic_sets, sets) {
    let inter_ref_pic_set_prediction_flag = false;
    if (stRpsIdx !== 0) {
        inter_ref_pic_set_prediction_flag = !!reader.next();
    }
    let delta_idx_minus1 = 0;
    let delta_rps_sign = false;
    let abs_delta_rps_minus1 = 0;
    const used_by_curr_pic_flag = [];
    const use_delta_flag = [];
    let num_negative_pics = 0;
    let num_positive_pics = 0;
    const delta_poc_s0_minus1 = [];
    const used_by_curr_pic_s0_flag = [];
    const delta_poc_s1_minus1 = [];
    const used_by_curr_pic_s1_flag = [];
    if (inter_ref_pic_set_prediction_flag) {
        if (stRpsIdx === num_short_term_ref_pic_sets) {
            delta_idx_minus1 = reader.decodeExponentialGolombNumber();
        }
        delta_rps_sign = !!reader.next();
        abs_delta_rps_minus1 = reader.decodeExponentialGolombNumber();
        const RefRpsIdx = stRpsIdx - (delta_idx_minus1 + 1);
        const RefRps = sets[RefRpsIdx];
        const NumDeltaPocs_RefRpsIdx = RefRps.num_negative_pics + RefRps.num_positive_pics;
        for (let j = 0; j <= NumDeltaPocs_RefRpsIdx; j += 1) {
            used_by_curr_pic_flag[j] = !!reader.next();
            if (!used_by_curr_pic_flag[j]) {
                use_delta_flag[j] = !!reader.next();
            }
            else {
                use_delta_flag[j] = true;
            }
        }
        const DeltaRps = (1 - 2 * Number(delta_rps_sign)) * (abs_delta_rps_minus1 + 1);
        const RefPocS0 = [];
        const RefPocS1 = [];
        const pocS0 = [];
        const pocS1 = [];
        let dPoc = 0;
        for (let i = 0; i < RefRps.num_negative_pics; i += 1) {
            dPoc -= RefRps.delta_poc_s0_minus1[i] + 1;
            RefPocS0[i] = dPoc;
        }
        dPoc = 0;
        for (let i = 0; i < RefRps.num_positive_pics; i += 1) {
            dPoc += RefRps.delta_poc_s1_minus1[i] + 1;
            RefPocS1[i] = dPoc;
        }
        let i = 0;
        if (RefRps.num_positive_pics > 0) {
            for (let j = RefRps.num_positive_pics - 1; j >= 0; j -= 1) {
                dPoc = RefPocS1[j] + DeltaRps;
                if (dPoc < 0 && use_delta_flag[RefRps.num_negative_pics + j]) {
                    pocS0[i] = dPoc;
                    used_by_curr_pic_s0_flag[i] =
                        used_by_curr_pic_flag[RefRps.num_negative_pics + j];
                    i += 1;
                }
            }
        }
        if (DeltaRps < 0 && use_delta_flag[NumDeltaPocs_RefRpsIdx]) {
            pocS0[i] = DeltaRps;
            used_by_curr_pic_s0_flag[i] =
                used_by_curr_pic_flag[NumDeltaPocs_RefRpsIdx];
            i += 1;
        }
        for (let j = 0; j < RefRps.num_negative_pics; j += 1) {
            dPoc = RefPocS0[j] + DeltaRps;
            if (dPoc < 0 && use_delta_flag[j]) {
                pocS0[i] = dPoc;
                used_by_curr_pic_s0_flag[i] = used_by_curr_pic_flag[j];
                i += 1;
            }
        }
        num_negative_pics = i;
        let prev = 0;
        for (i = 0; i < num_negative_pics; i += 1) {
            const current = pocS0[i];
            delta_poc_s0_minus1[i] = -(current - prev - 1);
            prev = current;
        }
        i = 0;
        if (RefRps.num_negative_pics > 0) {
            for (let j = RefRps.num_negative_pics - 1; j >= 0; j -= 1) {
                dPoc = RefPocS0[j] + DeltaRps;
                if (dPoc > 0 && use_delta_flag[j]) {
                    pocS1[i] = dPoc;
                    used_by_curr_pic_s1_flag[i] = used_by_curr_pic_flag[j];
                    i += 1;
                }
            }
        }
        if (DeltaRps > 0 && use_delta_flag[NumDeltaPocs_RefRpsIdx]) {
            pocS1[i] = DeltaRps;
            used_by_curr_pic_s1_flag[i] =
                used_by_curr_pic_flag[NumDeltaPocs_RefRpsIdx];
            i += 1;
        }
        for (let j = 0; j < RefRps.num_positive_pics; j += 1) {
            dPoc = RefPocS1[j] + DeltaRps;
            if (dPoc > 0 && use_delta_flag[RefRps.num_negative_pics + j]) {
                pocS1[i] = dPoc;
                used_by_curr_pic_s1_flag[i] =
                    used_by_curr_pic_flag[RefRps.num_negative_pics + j];
                i += 1;
            }
        }
        num_positive_pics = i;
        prev = 0;
        for (i = 0; i < num_positive_pics; i += 1) {
            const current = pocS1[i];
            delta_poc_s1_minus1[i] = current - prev - 1;
            prev = current;
        }
    }
    else {
        num_negative_pics = reader.decodeExponentialGolombNumber();
        num_positive_pics = reader.decodeExponentialGolombNumber();
        for (let i = 0; i < num_negative_pics; i += 1) {
            delta_poc_s0_minus1[i] = reader.decodeExponentialGolombNumber();
            used_by_curr_pic_s0_flag[i] = !!reader.next();
        }
        for (let i = 0; i < num_positive_pics; i += 1) {
            delta_poc_s1_minus1[i] = reader.decodeExponentialGolombNumber();
            used_by_curr_pic_s1_flag[i] = !!reader.next();
        }
    }
    return {
        stRpsIdx,
        num_short_term_ref_pic_sets,
        inter_ref_pic_set_prediction_flag,
        delta_idx_minus1,
        delta_rps_sign,
        abs_delta_rps_minus1,
        used_by_curr_pic_flag,
        use_delta_flag,
        num_negative_pics,
        num_positive_pics,
        delta_poc_s0_minus1,
        used_by_curr_pic_s0_flag,
        delta_poc_s1_minus1,
        used_by_curr_pic_s1_flag,
    };
}
/**
 * E.2.1 VUI parameters syntax
 */
export function h265ParseVuiParameters(reader) {
    const aspect_ratio_info_present_flag = !!reader.next();
    let aspect_ratio_idc;
    let sar_width;
    let sar_height;
    if (aspect_ratio_info_present_flag) {
        aspect_ratio_idc = reader.read(8);
        if (aspect_ratio_idc === 255) {
            sar_width = reader.read(16);
            sar_height = reader.read(16);
        }
    }
    const overscan_info_present_flag = !!reader.next();
    let overscan_appropriate_flag;
    if (overscan_info_present_flag) {
        overscan_appropriate_flag = !!reader.next();
    }
    const video_signal_type_present_flag = !!reader.next();
    let video_format;
    let video_full_range_flag;
    let colour_description_present_flag;
    let colour_primaries;
    let transfer_characteristics;
    let matrix_coeffs;
    if (video_signal_type_present_flag) {
        video_format = reader.read(3);
        video_full_range_flag = !!reader.next();
        colour_description_present_flag = !!reader.next();
        if (colour_description_present_flag) {
            colour_primaries = reader.read(8);
            transfer_characteristics = reader.read(8);
            matrix_coeffs = reader.read(8);
        }
    }
    const chroma_loc_info_present_flag = !!reader.next();
    let chroma_sample_loc_type_top_field;
    let chroma_sample_loc_type_bottom_field;
    if (chroma_loc_info_present_flag) {
        chroma_sample_loc_type_top_field =
            reader.decodeExponentialGolombNumber();
        chroma_sample_loc_type_bottom_field =
            reader.decodeExponentialGolombNumber();
    }
    const neutral_chroma_indication_flag = !!reader.next();
    const field_seq_flag = !!reader.next();
    const frame_field_info_present_flag = !!reader.next();
    const default_display_window_flag = !!reader.next();
    let def_disp_win_left_offset;
    let def_disp_win_right_offset;
    let def_disp_win_top_offset;
    let def_disp_win_bottom_offset;
    if (default_display_window_flag) {
        def_disp_win_left_offset = reader.decodeExponentialGolombNumber();
        def_disp_win_right_offset = reader.decodeExponentialGolombNumber();
        def_disp_win_top_offset = reader.decodeExponentialGolombNumber();
        def_disp_win_bottom_offset = reader.decodeExponentialGolombNumber();
    }
    const vui_timing_info_present_flag = !!reader.next();
    let vui_num_units_in_tick;
    let vui_time_scale;
    let vui_poc_proportional_to_timing_flag;
    let vui_num_ticks_poc_diff_one_minus1;
    let vui_hrd_parameters_present_flag;
    if (vui_timing_info_present_flag) {
        vui_num_units_in_tick = reader.read(32);
        vui_time_scale = reader.read(32);
        vui_poc_proportional_to_timing_flag = !!reader.next();
        if (vui_poc_proportional_to_timing_flag) {
            vui_num_ticks_poc_diff_one_minus1 =
                reader.decodeExponentialGolombNumber();
        }
        vui_hrd_parameters_present_flag = !!reader.next();
        if (vui_hrd_parameters_present_flag) {
            throw new Error("Not implemented");
        }
    }
    const bitstream_restriction_flag = !!reader.next();
    let tiles_fixed_structure_flag;
    let motion_vectors_over_pic_boundaries_flag;
    let restricted_ref_pic_lists_flag;
    let min_spatial_segmentation_idc;
    let max_bytes_per_pic_denom;
    let max_bits_per_min_cu_denom;
    let log2_max_mv_length_horizontal;
    let log2_max_mv_length_vertical;
    if (bitstream_restriction_flag) {
        tiles_fixed_structure_flag = !!reader.next();
        motion_vectors_over_pic_boundaries_flag = !!reader.next();
        restricted_ref_pic_lists_flag = !!reader.next();
        min_spatial_segmentation_idc = reader.decodeExponentialGolombNumber();
        max_bytes_per_pic_denom = reader.decodeExponentialGolombNumber();
        max_bits_per_min_cu_denom = reader.decodeExponentialGolombNumber();
        log2_max_mv_length_horizontal = reader.decodeExponentialGolombNumber();
        log2_max_mv_length_vertical = reader.decodeExponentialGolombNumber();
    }
    return {
        aspect_ratio_info_present_flag,
        aspect_ratio_idc,
        sar_width,
        sar_height,
        overscan_info_present_flag,
        overscan_appropriate_flag,
        video_signal_type_present_flag,
        video_format,
        video_full_range_flag,
        colour_description_present_flag,
        colour_primaries,
        transfer_characteristics,
        matrix_coeffs,
        chroma_loc_info_present_flag,
        chroma_sample_loc_type_top_field,
        chroma_sample_loc_type_bottom_field,
        neutral_chroma_indication_flag,
        field_seq_flag,
        frame_field_info_present_flag,
        default_display_window_flag,
        def_disp_win_left_offset,
        def_disp_win_right_offset,
        def_disp_win_top_offset,
        def_disp_win_bottom_offset,
        vui_timing_info_present_flag,
        vui_num_units_in_tick,
        vui_time_scale,
        vui_poc_proportional_to_timing_flag,
        vui_num_ticks_poc_diff_one_minus1,
        vui_hrd_parameters_present_flag,
        bitstream_restriction_flag,
        tiles_fixed_structure_flag,
        motion_vectors_over_pic_boundaries_flag,
        restricted_ref_pic_lists_flag,
        min_spatial_segmentation_idc,
        max_bytes_per_pic_denom,
        max_bits_per_min_cu_denom,
        log2_max_mv_length_horizontal,
        log2_max_mv_length_vertical,
    };
}
/**
 * E.2.2 HRD parameters syntax
 */
export function h265ParseHrdParameters(reader, commonInfPresentFlag, maxNumSubLayersMinus1) {
    let nal_hrd_parameters_present_flag;
    let vcl_hrd_parameters_present_flag;
    let sub_pic_hrd_params_present_flag;
    let tick_divisor_minus2;
    let du_cpb_removal_delay_increment_length_minus1;
    let sub_pic_cpb_params_in_pic_timing_sei_flag;
    let dpb_output_delay_du_length_minus1;
    let bit_rate_scale;
    let cpb_size_scale;
    let cpb_size_du_scale;
    let initial_cpb_removal_delay_length_minus1;
    let au_cpb_removal_delay_length_minus1;
    let dpb_output_delay_length_minus1;
    if (commonInfPresentFlag) {
        nal_hrd_parameters_present_flag = !!reader.next();
        vcl_hrd_parameters_present_flag = !!reader.next();
        if (nal_hrd_parameters_present_flag ||
            vcl_hrd_parameters_present_flag) {
            sub_pic_hrd_params_present_flag = !!reader.next();
            if (sub_pic_hrd_params_present_flag) {
                tick_divisor_minus2 = reader.read(8);
                du_cpb_removal_delay_increment_length_minus1 = reader.read(5);
                sub_pic_cpb_params_in_pic_timing_sei_flag = !!reader.next();
                dpb_output_delay_du_length_minus1 = reader.read(5);
            }
            bit_rate_scale = reader.read(4);
            cpb_size_scale = reader.read(4);
            if (sub_pic_hrd_params_present_flag) {
                cpb_size_du_scale = reader.read(4);
            }
            initial_cpb_removal_delay_length_minus1 = reader.read(5);
            au_cpb_removal_delay_length_minus1 = reader.read(5);
            dpb_output_delay_length_minus1 = reader.read(5);
        }
    }
    const fixed_pic_rate_general_flag = [];
    const fixed_pic_rate_within_cvs_flag = [];
    const elemental_duration_in_tc_minus1 = [];
    const low_delay_hrd_flag = [];
    const cpb_cnt_minus1 = [];
    const nalHrdParameters = [];
    const vclHrdParameters = [];
    for (let i = 0; i <= maxNumSubLayersMinus1; i += 1) {
        fixed_pic_rate_general_flag[i] = !!reader.next();
        if (!fixed_pic_rate_general_flag[i]) {
            fixed_pic_rate_within_cvs_flag[i] = !!reader.next();
        }
        if (fixed_pic_rate_within_cvs_flag[i]) {
            elemental_duration_in_tc_minus1[i] =
                reader.decodeExponentialGolombNumber();
        }
        else {
            low_delay_hrd_flag[i] = !!reader.next();
        }
        if (!low_delay_hrd_flag[i]) {
            cpb_cnt_minus1[i] = reader.decodeExponentialGolombNumber();
        }
        if (nal_hrd_parameters_present_flag) {
            nalHrdParameters[i] = h265ParseSubLayerHrdParameters(reader, i, getCpbCnt(cpb_cnt_minus1[i]));
        }
        if (vcl_hrd_parameters_present_flag) {
            vclHrdParameters[i] = h265ParseSubLayerHrdParameters(reader, i, getCpbCnt(cpb_cnt_minus1[i]));
        }
    }
    return {
        nal_hrd_parameters_present_flag,
        vcl_hrd_parameters_present_flag,
        sub_pic_hrd_params_present_flag,
        tick_divisor_minus2,
        du_cpb_removal_delay_increment_length_minus1,
        sub_pic_cpb_params_in_pic_timing_sei_flag,
        dpb_output_delay_du_length_minus1,
        bit_rate_scale,
        cpb_size_scale,
        cpb_size_du_scale,
        initial_cpb_removal_delay_length_minus1,
        au_cpb_removal_delay_length_minus1,
        dpb_output_delay_length_minus1,
        fixed_pic_rate_general_flag,
        fixed_pic_rate_within_cvs_flag,
        elemental_duration_in_tc_minus1,
        low_delay_hrd_flag,
        cpb_cnt_minus1,
        nalHrdParameters,
        vclHrdParameters,
    };
}
/**
 * E.2.3 Sub-layer HRD parameters syntax
 */
export function h265ParseSubLayerHrdParameters(reader, subLayerId, CpbCnt) {
    const bit_rate_value_minus1 = [];
    const cpb_size_value_minus1 = [];
    const cpb_size_du_value_minus1 = [];
    const bit_rate_du_value_minus1 = [];
    const cbr_flag = [];
    for (let i = 0; i < CpbCnt; i += 1) {
        bit_rate_value_minus1[i] = reader.decodeExponentialGolombNumber();
        cpb_size_value_minus1[i] = reader.decodeExponentialGolombNumber();
        if (subLayerId > 0) {
            cbr_flag[i] = !!reader.next();
        }
    }
    return {
        bit_rate_value_minus1,
        cpb_size_value_minus1,
        cpb_size_du_value_minus1,
        bit_rate_du_value_minus1,
        cbr_flag,
    };
}
/**
 * E.3.3 Sub-layer HRD parameters semantics
 */
function getCpbCnt(cpb_cnt_minus_1) {
    return cpb_cnt_minus_1 + 1;
}
export function h265SearchConfiguration(buffer) {
    let videoParameterSet;
    let sequenceParameterSet;
    let pictureParameterSet;
    let count = 0;
    for (const nalu of annexBSplitNalu(buffer)) {
        const header = h265ParseNaluHeader(nalu);
        const raw = Object.assign(Object.assign({}, header), { data: nalu, rbsp: nalu.subarray(2) });
        switch (header.nal_unit_type) {
            case 32:
                videoParameterSet = raw;
                break;
            case 33:
                sequenceParameterSet = raw;
                break;
            case 34:
                pictureParameterSet = raw;
                break;
            default:
                continue;
        }
        count += 1;
        if (count === 3) {
            return {
                videoParameterSet,
                sequenceParameterSet,
                pictureParameterSet,
            };
        }
    }
    throw new Error("Invalid data");
}
export function h265ParseSpsMultilayerExtension(reader) {
    const inter_view_mv_vert_constraint_flag = !!reader.next();
    return {
        inter_view_mv_vert_constraint_flag,
    };
}
export function h265ParseSps3dExtension(reader) {
    const iv_di_mc_enabled_flag = [];
    const iv_mv_scal_enabled_flag = [];
    iv_di_mc_enabled_flag[0] = !!reader.next();
    iv_mv_scal_enabled_flag[0] = !!reader.next();
    const log2_ivmc_sub_pb_size_minus3 = reader.decodeExponentialGolombNumber();
    const iv_res_pred_enabled_flag = !!reader.next();
    const depth_ref_enabled_flag = !!reader.next();
    const vsp_mc_enabled_flag = !!reader.next();
    const dbbp_enabled_flag = !!reader.next();
    iv_di_mc_enabled_flag[1] = !!reader.next();
    iv_mv_scal_enabled_flag[1] = !!reader.next();
    const tex_mc_enabled_flag = !!reader.next();
    const log2_texmc_sub_pb_size_minus3 = reader.decodeExponentialGolombNumber();
    const intra_contour_enabled_flag = !!reader.next();
    const intra_dc_only_wedge_enabled_flag = !!reader.next();
    const cqt_cu_part_pred_enabled_flag = !!reader.next();
    const inter_dc_only_enabled_flag = !!reader.next();
    const skip_intra_enabled_flag = !!reader.next();
    return {
        iv_di_mc_enabled_flag,
        iv_mv_scal_enabled_flag,
        log2_ivmc_sub_pb_size_minus3,
        iv_res_pred_enabled_flag,
        depth_ref_enabled_flag,
        vsp_mc_enabled_flag,
        dbbp_enabled_flag,
        tex_mc_enabled_flag,
        log2_texmc_sub_pb_size_minus3,
        intra_contour_enabled_flag,
        intra_dc_only_wedge_enabled_flag,
        cqt_cu_part_pred_enabled_flag,
        inter_dc_only_enabled_flag,
        skip_intra_enabled_flag,
    };
}
export function h265ParseConfiguration(data) {
    const { videoParameterSet, sequenceParameterSet, pictureParameterSet } = h265SearchConfiguration(data);
    const { profileTierLevel: { generalProfileTier: { profile_space: generalProfileSpace, tier_flag: generalTierFlag, profile_idc: generalProfileIndex, profileCompatibilitySet: generalProfileCompatibilitySet, constraintSet: generalConstraintSet, }, general_level_idc: generalLevelIndex, }, } = h265ParseVideoParameterSet(videoParameterSet.rbsp);
    const { chroma_format_idc, pic_width_in_luma_samples: encodedWidth, pic_height_in_luma_samples: encodedHeight, conf_win_left_offset: cropLeft = 0, conf_win_right_offset: cropRight = 0, conf_win_top_offset: cropTop = 0, conf_win_bottom_offset: cropBottom = 0, } = h265ParseSequenceParameterSet(sequenceParameterSet.rbsp);
    const SubWidthC = getSubWidthC(chroma_format_idc);
    const SubHeightC = getSubHeightC(chroma_format_idc);
    const croppedWidth = encodedWidth - SubWidthC * (cropLeft + cropRight);
    const croppedHeight = encodedHeight - SubHeightC * (cropTop + cropBottom);
    return {
        videoParameterSet,
        sequenceParameterSet,
        pictureParameterSet,
        generalProfileSpace,
        generalProfileIndex,
        generalProfileCompatibilitySet,
        generalTierFlag,
        generalLevelIndex,
        generalConstraintSet,
        encodedWidth,
        encodedHeight,
        cropLeft,
        cropRight,
        cropTop,
        cropBottom,
        croppedWidth,
        croppedHeight,
    };
}