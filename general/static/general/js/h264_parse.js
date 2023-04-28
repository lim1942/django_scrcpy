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
// From https://developer.android.com/reference/android/media/MediaCodecInfo.CodecProfileLevel
export var AndroidAvcProfile;
(function (AndroidAvcProfile) {
    AndroidAvcProfile[AndroidAvcProfile["Baseline"] = 1] = "Baseline";
    AndroidAvcProfile[AndroidAvcProfile["Main"] = 2] = "Main";
    AndroidAvcProfile[AndroidAvcProfile["Extended"] = 4] = "Extended";
    AndroidAvcProfile[AndroidAvcProfile["High"] = 8] = "High";
    AndroidAvcProfile[AndroidAvcProfile["High10"] = 16] = "High10";
    AndroidAvcProfile[AndroidAvcProfile["High422"] = 32] = "High422";
    AndroidAvcProfile[AndroidAvcProfile["High444"] = 64] = "High444";
    AndroidAvcProfile[AndroidAvcProfile["ConstrainedBaseline"] = 65536] = "ConstrainedBaseline";
    AndroidAvcProfile[AndroidAvcProfile["ConstrainedHigh"] = 524288] = "ConstrainedHigh";
})(AndroidAvcProfile || (AndroidAvcProfile = {}));
export var AndroidAvcLevel;
(function (AndroidAvcLevel) {
    AndroidAvcLevel[AndroidAvcLevel["Level1"] = 1] = "Level1";
    AndroidAvcLevel[AndroidAvcLevel["Level1b"] = 2] = "Level1b";
    AndroidAvcLevel[AndroidAvcLevel["Level11"] = 4] = "Level11";
    AndroidAvcLevel[AndroidAvcLevel["Level12"] = 8] = "Level12";
    AndroidAvcLevel[AndroidAvcLevel["Level13"] = 16] = "Level13";
    AndroidAvcLevel[AndroidAvcLevel["Level2"] = 32] = "Level2";
    AndroidAvcLevel[AndroidAvcLevel["Level21"] = 64] = "Level21";
    AndroidAvcLevel[AndroidAvcLevel["Level22"] = 128] = "Level22";
    AndroidAvcLevel[AndroidAvcLevel["Level3"] = 256] = "Level3";
    AndroidAvcLevel[AndroidAvcLevel["Level31"] = 512] = "Level31";
    AndroidAvcLevel[AndroidAvcLevel["Level32"] = 1024] = "Level32";
    AndroidAvcLevel[AndroidAvcLevel["Level4"] = 2048] = "Level4";
    AndroidAvcLevel[AndroidAvcLevel["Level41"] = 4096] = "Level41";
    AndroidAvcLevel[AndroidAvcLevel["Level42"] = 8192] = "Level42";
    AndroidAvcLevel[AndroidAvcLevel["Level5"] = 16384] = "Level5";
    AndroidAvcLevel[AndroidAvcLevel["Level51"] = 32768] = "Level51";
    AndroidAvcLevel[AndroidAvcLevel["Level52"] = 65536] = "Level52";
    AndroidAvcLevel[AndroidAvcLevel["Level6"] = 131072] = "Level6";
    AndroidAvcLevel[AndroidAvcLevel["Level61"] = 262144] = "Level61";
    AndroidAvcLevel[AndroidAvcLevel["Level62"] = 524288] = "Level62";
})(AndroidAvcLevel || (AndroidAvcLevel = {}));
// H.264 has two standards: ITU-T H.264 and ISO/IEC 14496-10
// they have the same content, and refer themselves as "H.264".
// The name "AVC" (Advanced Video Coding) is only used in ISO spec name,
// and other ISO specs referring to H.264.
// Because this module parses H.264 Annex B format,
// it's named "h264" instead of "avc".
// 7.3.2.1.1 Sequence parameter set data syntax
// Variable names in this method uses the snake_case convention as in the spec for easier referencing.
export function h264ParseSequenceParameterSet(nalu) {
    const reader = new NaluSodbBitReader(nalu);
    if (reader.next() !== 0) {
        throw new Error("Invalid data");
    }
    const nal_ref_idc = reader.read(2);
    const nal_unit_type = reader.read(5);
    if (nal_unit_type !== 7) {
        throw new Error("Invalid data");
    }
    if (nal_ref_idc === 0) {
        throw new Error("Invalid data");
    }
    const profile_idc = reader.read(8);
    const constraint_set = reader.peek(8);
    const constraint_set0_flag = !!reader.next();
    const constraint_set1_flag = !!reader.next();
    const constraint_set2_flag = !!reader.next();
    const constraint_set3_flag = !!reader.next();
    const constraint_set4_flag = !!reader.next();
    const constraint_set5_flag = !!reader.next();
    // reserved_zero_2bits
    if (reader.read(2) !== 0) {
        throw new Error("Invalid data");
    }
    const level_idc = reader.read(8);
    const seq_parameter_set_id = reader.decodeExponentialGolombNumber();
    if (profile_idc === 100 ||
        profile_idc === 110 ||
        profile_idc === 122 ||
        profile_idc === 244 ||
        profile_idc === 44 ||
        profile_idc === 83 ||
        profile_idc === 86 ||
        profile_idc === 118 ||
        profile_idc === 128 ||
        profile_idc === 138 ||
        profile_idc === 139 ||
        profile_idc === 134) {
        const chroma_format_idc = reader.decodeExponentialGolombNumber();
        if (chroma_format_idc === 3) {
            // separate_colour_plane_flag
            reader.next();
        }
        // bit_depth_luma_minus8
        reader.decodeExponentialGolombNumber();
        // bit_depth_chroma_minus8
        reader.decodeExponentialGolombNumber();
        // qpprime_y_zero_transform_bypass_flag
        reader.next();
        const seq_scaling_matrix_present_flag = !!reader.next();
        if (seq_scaling_matrix_present_flag) {
            const seq_scaling_list_present_flag = [];
            for (let i = 0; i < (chroma_format_idc !== 3 ? 8 : 12); i += 1) {
                seq_scaling_list_present_flag[i] = !!reader.next();
                if (seq_scaling_list_present_flag[i])
                    if (i < 6) {
                        // TODO
                        // scaling_list( ScalingList4x4[ i ], 16,
                        //               UseDefaultScalingMatrix4x4Flag[ i ])
                    }
                    else {
                        // TODO
                        // scaling_list( ScalingList8x8[ i − 6 ], 64,
                        //               UseDefaultScalingMatrix8x8Flag[ i − 6 ] )
                    }
            }
        }
    }
    // log2_max_frame_num_minus4
    reader.decodeExponentialGolombNumber();
    const pic_order_cnt_type = reader.decodeExponentialGolombNumber();
    if (pic_order_cnt_type === 0) {
        // log2_max_pic_order_cnt_lsb_minus4
        reader.decodeExponentialGolombNumber();
    }
    else if (pic_order_cnt_type === 1) {
        // delta_pic_order_always_zero_flag
        reader.next();
        // offset_for_non_ref_pic
        reader.decodeExponentialGolombNumber();
        // offset_for_top_to_bottom_field
        reader.decodeExponentialGolombNumber();
        const num_ref_frames_in_pic_order_cnt_cycle = reader.decodeExponentialGolombNumber();
        const offset_for_ref_frame = [];
        for (let i = 0; i < num_ref_frames_in_pic_order_cnt_cycle; i += 1) {
            offset_for_ref_frame[i] = reader.decodeExponentialGolombNumber();
        }
    }
    // max_num_ref_frames
    reader.decodeExponentialGolombNumber();
    // gaps_in_frame_num_value_allowed_flag
    reader.next();
    const pic_width_in_mbs_minus1 = reader.decodeExponentialGolombNumber();
    const pic_height_in_map_units_minus1 = reader.decodeExponentialGolombNumber();
    const frame_mbs_only_flag = reader.next();
    if (!frame_mbs_only_flag) {
        // mb_adaptive_frame_field_flag
        reader.next();
    }
    // direct_8x8_inference_flag
    reader.next();
    const frame_cropping_flag = !!reader.next();
    let frame_crop_left_offset;
    let frame_crop_right_offset;
    let frame_crop_top_offset;
    let frame_crop_bottom_offset;
    if (frame_cropping_flag) {
        frame_crop_left_offset = reader.decodeExponentialGolombNumber();
        frame_crop_right_offset = reader.decodeExponentialGolombNumber();
        frame_crop_top_offset = reader.decodeExponentialGolombNumber();
        frame_crop_bottom_offset = reader.decodeExponentialGolombNumber();
    }
    else {
        frame_crop_left_offset = 0;
        frame_crop_right_offset = 0;
        frame_crop_top_offset = 0;
        frame_crop_bottom_offset = 0;
    }
    const vui_parameters_present_flag = !!reader.next();
    if (vui_parameters_present_flag) {
        // TODO
        // vui_parameters( )
    }
    return {
        profile_idc,
        constraint_set,
        constraint_set0_flag,
        constraint_set1_flag,
        constraint_set2_flag,
        constraint_set3_flag,
        constraint_set4_flag,
        constraint_set5_flag,
        level_idc,
        seq_parameter_set_id,
        pic_width_in_mbs_minus1,
        pic_height_in_map_units_minus1,
        frame_mbs_only_flag,
        frame_cropping_flag,
        frame_crop_left_offset,
        frame_crop_right_offset,
        frame_crop_top_offset,
        frame_crop_bottom_offset,
    };
}
/**
 * Find Sequence Parameter Set (SPS) and Picture Parameter Set (PPS)
 * from H.264 Annex B formatted data.
 */
export function h264SearchConfiguration(buffer) {
    let sequenceParameterSet;
    let pictureParameterSet;
    for (const nalu of annexBSplitNalu(buffer)) {
        const naluType = nalu[0] & 0x1f;
        switch (naluType) {
            case 7: // Sequence parameter set
                sequenceParameterSet = nalu;
                if (pictureParameterSet) {
                    return {
                        sequenceParameterSet,
                        pictureParameterSet,
                    };
                }
                break;
            case 8: // Picture parameter set
                pictureParameterSet = nalu;
                if (sequenceParameterSet) {
                    return {
                        sequenceParameterSet,
                        pictureParameterSet,
                    };
                }
                break;
            default:
                // ignore
                break;
        }
    }
    throw new Error("Invalid data");
}
export function h264ParseConfiguration(data) {
    const { sequenceParameterSet, pictureParameterSet } = h264SearchConfiguration(data);
    const { profile_idc: profileIndex, constraint_set: constraintSet, level_idc: levelIndex, pic_width_in_mbs_minus1, pic_height_in_map_units_minus1, frame_mbs_only_flag, frame_crop_left_offset, frame_crop_right_offset, frame_crop_top_offset, frame_crop_bottom_offset, } = h264ParseSequenceParameterSet(sequenceParameterSet);
    const encodedWidth = (pic_width_in_mbs_minus1 + 1) * 16;
    const encodedHeight = (pic_height_in_map_units_minus1 + 1) * (2 - frame_mbs_only_flag) * 16;
    const cropLeft = frame_crop_left_offset * 2;
    const cropRight = frame_crop_right_offset * 2;
    const cropTop = frame_crop_top_offset * 2;
    const cropBottom = frame_crop_bottom_offset * 2;
    const croppedWidth = encodedWidth - cropLeft - cropRight;
    const croppedHeight = encodedHeight - cropTop - cropBottom;
    return {
        pictureParameterSet,
        sequenceParameterSet,
        profileIndex,
        constraintSet,
        levelIndex,
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
