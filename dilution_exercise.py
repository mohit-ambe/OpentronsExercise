from opentrons import protocol_api
import pandas as pd
import json

__author__ = "Mohit Ambe"
__email__ = "mohitambe77@gmail.com"

metadata = {'apiLevel': '2.10'}


def run(protocol: protocol_api.ProtocolContext):
    # robot needs to know what each labware component is
    LABWARE = {'reservoir': 'thermo_12002301_microplate_reservoir_1well_pp_96pbottom_sw_300000ul',
               'start': 'gbo_675801_microplate_96well_ps_fbottom_rw_199ul_uvstar_halfarea',
               'dilution': 'gbo_650101_microplate_96well_ps_ubottom_rw_323ul'}

    # robot needs to know where each labware is
    PLATE_RACKS = {'reservoir': 11,  # reservoir
                   'start': 10,  # bravo plate
                   'dilution': 7  # output plate
                   }

    # robot needs to know what type of tip only p20 is used here is on what racks (tips can be on more than 1 rack)
    TIP_RACKS = {20: [8]}

    # actually load the labware
    plates = {}
    for k in PLATE_RACKS:
        with open('./labware/' + LABWARE[k] + '.json', 'r') as f:
            plate_def = json.load(f)
            plates[k] = protocol.load_labware_from_definition(plate_def, PLATE_RACKS[k])

    tips = {}
    for k in TIP_RACKS:
        tips[k] = []
        for rack in TIP_RACKS[k]:
            tips[k] += [protocol.load_labware('opentrons_96_tiprack_{}ul'.format(k), rack)]

    # these are the actual pipettes that move things around
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=tips[20])

    # read input into pandas dataframe
    # r_10_con contains all of the concentrations of samples A1-H1 on rack 10
    r_10_con = pd.read_csv("input.csv")

    # TODO: PERFORM THE DILUTION FROM COLUMN 1 of START PLATE TO COLUMN 1 of DILUTION PLATE
    # s.t. concentration of all samples in dilution plate is 9 ug/mL
    # Easiest method is to iterate through the input dataframe and add the appropriate amount of reservoir
    # then iterate again and add the appropriate amount of sample.  This is to save tips.
    # EXAMPLE MOVE: take 15 mL of the sample in A1 of the start plate and dispense it in A1 of the dilution plate
    # p20.pick_up_tip()
    # p20.aspirate(15,plates['start']['A1'])
    # p20.dispense(15,plates['dilution']['A1'])

    # f_con is the desired final concentration of the dilution in rack 7
    # s_v is the sample volume taken from a certain sample on rack 10
    f_con = 9
    # iterate through all rows of the csv file
    for i in range(0, r_10_con.shape[0]):
        con = r_10_con.iloc[i, 1]
        # calculate the required sample volume
        # Explanation for this equation in attached txt (Dilution Exercise Explanation)
        s_v = 180 / (1 + (con - f_con) / f_con)
        # recalculates final concentration of dilution
        # should be 9, or a decimal that approximates to 9

        # print(r_10_con.iloc[i, 0], s_v, con*s_v/180)

        well_index = r_10_con.iloc[i, 0]
        b_v = 180 - s_v

        # if s_v <= 20:
        #     transfer_and_dilute(s_v, b_v)
        # else:
        #     s_v = 20
        #     b_v = ((s_v * con) / f_con) - s_v
        #     transfer_and_dilute(s_v, b_v)
        
        # the if statement below is an optimized version of this commented if block
        if s_v > 20:
            s_v = 20
            b_v = ((s_v * con) / f_con) - s_v
        print(well_index, s_v, b_v)

        # transfer solution from rack 10 to rack 7
        p20.pick_up_tip()
        p20.aspirate(s_v, plates['start'][well_index])
        p20.dispense(s_v, plates['dilution'][well_index])
        p20.drop_tip()

        # transfer buffer from reservoir to rack 7
        # needs to be done in a loop because a p20_single_gen2 pipette can only hold 20 uL
        # and buffer volume needed is more than 20uL
        # using only one tip here because the tip will only be aspirating from one well(buffer)
        p20.pick_up_tip()
        while b_v > 0:
              if b_v > 20:
                p20.aspirate(20, plates['reservoir'][well_index])
                p20.dispense(20, plates['dilution'][well_index])
                b_v -= 20
              else:
                p20.aspirate(b_v, plates['reservoir'][well_index])
                p20.dispense(b_v, plates['dilution'][well_index])
                break
        p20.drop_tip()
