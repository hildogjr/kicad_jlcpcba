# Create a JLCPCB PCBA set of files to support PCBA, this requires us to
# produce a BOM file and a CPL (component placement file), which will be a
# .pos file.
# We do this by reading the associated schematic (mainly for part numbers)
# and then cross-matching the pcb modules.

import pcbnew
import os
import re


def read_rotation_db(filename):
    '''Read the rotations.cf config file so we know what rotations
    to apply later.
    '''
    db = []
    fh = open(filename, 'r')
    for line in fh:
        line = line.rstrip()
        line = re.sub('#.*$', '', line)         # remove anything after a comment
        line = re.sub('\s*$', '', line)         # remove all trailing space
        if (line == ""):
            continue
        m = re.match('^([^\s]+)\s+(\d+)$', line)
        if m:
            db.append((m.group(1), int(m.group(2))))
    return db


def possible_rotate(footprint):
    '''Given the footprint name, work out what rotation is needed, we
    support matching against the long or short footprint names (if there
    is a colon in the regex).
    '''
    fpshort = footprint.split(':')[-1]
    for rot in rotation_db:
        ex = rot[0]
        delta = rot[1]
        fp = fpshort
        if (re.search(':', ex)):
            fp = footprint
        if(re.search(ex, fp)):
            return delta
    return 0


def create_pcba():
    '''Main function to creates the files.
    '''
    global rotation_db

    board = pcbnew.GetBoard()
    boardfile = board.GetFileName()
    project_path = os.path.dirname(boardfile)
    projet_name = os.path.splitext(os.path.basename(boardfile))[0]

    # Populate the rotation db (do it here so editing and retrying is easy).
    rotation_db = read_rotation_db(os.path.join(os.path.dirname(__file__), 'rotations.cf'))
    
    # Open both layer files...
    top_file = os.path.join(project_path, projet_name) + '_JLCPCB_top_Pos.csv'
    top_fh = open(top_file, 'w')
    top_fh.write('Designator,Val,Package,Mid X,Mid Y,Rotation,Layer\n')

    bottom_file = os.path.join(project_path, projet_name) + '_JLCPCB_bottom_Pos.csv'
    bottom_fh = open(bottom_file, 'w')
    bottom_fh.write('Designator,Val,Package,Mid X,Mid Y,Rotation,Layer\n')

    bom_list = {}
    for f in board.GetFootprints():
        
        # Check if it is a SMD component, PHT components are node assembled
        # by JCLPCB on the default production line.
        if not(f.GetAttributes() & pcbnew.FP_SMD) or (f.GetAttributes() & \
                (pcbnew.FP_BOARD_ONLY + pcbnew.FP_EXCLUDE_FROM_POS_FILES + pcbnew.FP_BOARD_ONLY)):
            continue

        # Add item to the BOM creating a `set()`.
        reference = f.GetReference()
        value = f.GetValue()
        # Check the typed name for the LCSC stock code filed name.
        lcsc_field_name = 'lcsc'
        for field_name in f.GetProperties().keys():
            if field_name.lower() == 'lcsc' or field_name.lower() == 'lcsc#':
                lcsc_field_name = field_name
                break
        lcsc_code = f.GetProperty(lcsc_field_name)

        if not(re.search('\d$', reference) and re.search('\d', value)) and lcsc_field_name:
            # The reference must have a numeric ending, usually Pcbnew
            # use G*** or this kind of termination for footprints that
            # does not represent parts.
            # Also the value have to have number, usually the designer
            # assign "not populate" / "n/a" (not applicable) ... to parts
            # on layout that may be assembled later.
            # To have some expection, in case of LCSC stock code present,
            # this part will be considered.
            continue

        try:
            footprint = str(f.GetFPID().GetLibItemName())
        except:
            footprint = None
        if not lcsc_code:
            lcsc_code = str(None)  # It will be selected after at JLCPCB interface.
        if reference and value and footprint:
            #footprint = footprint.split(':')[-1] # Simplify the footprint name.
            key = value + '//' + footprint + '//' + lcsc_code
            if (not key in bom_list):
                bom_list[key] = set()
            bom_list[key].add(reference)

        # Get the position of the component. Internally, Pcbnew uses
        # micrometer position unit and a tenth of degrees on rotation.
        x = - f.GetX() / 1000000.0
        y = - f.GetY() / 1000000.0
        rotation = f.GetOrientationDegrees()  # Alredy give the converted value.
        rotation = (rotation + possible_rotate(footprint)) % 360

        # Write the component to the correspondent position file.
        # Use `f.GetLayer()` instead `f.GetLayerName()` because v6
        # will allow layer rename.
        fh = (bottom_fh if f.GetLayer() & pcbnew.SIDE_TOP else top_fh)
        layer_name = ('bottom' if f.GetLayer() & pcbnew.SIDE_TOP else 'top')
        fh.write('"' + reference + '","' + value + '","' + footprint + '",' +
                 str(x) + ',' + str(y) + ',' + str(rotation) + ',' + layer_name + '\n')

    top_fh.close()
    bottom_fh.close()


    # Write the BOM.
    bom_file = os.path.join(project_path, projet_name) + '_JLCPCB_BoM.csv'
    bom_fh = open(bom_file, 'w')
    bom_fh.write('Comment,Designator,Footprint,LCSC\n')

    for k, v in bom_list.items():
        value, footprint, lcsc = re.split("//", k)
        references = ','.join(v)
        bom_fh.write('"' + value + '","' + references + '","' +
                    footprint + '","' + lcsc + '"\n')

    bom_fh.close()
