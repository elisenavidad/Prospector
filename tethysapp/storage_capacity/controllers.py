from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tethys_sdk.gizmos import TableView, LinePlot, Button, SelectInput, TextInput

from math import pi, log10

from .model import SessionMaker, FlowDurationData
import json, sys, cgi


@login_required()
def home(request):
    """
    Controller for the app home page.
    """
    session=SessionMaker()

    pipeRoughness={'Riveted Steel': 0.0009, 'Concrete': 0.0003, 'Wood Stave': 0.00018,
        'Cast Iron': 0.00026, 'Galvanized Iron': 0.00015, 'Commercial Steel': 0.000045,
        'Drawn Turbing': 0.0000015, 'Plastic': 0, 'Glass': 0}

    materialSelectInput = []
    for v, k in pipeRoughness.iteritems():
        materialSelectInput.append((v, float(k)))

    materialDropdown = SelectInput(display_text='Select Pipe Material',
                                   name='materialDropdown',
                                   multiple=False,
                                   options=materialSelectInput,
                                   initial=['Commercial Steel'],
                                   original=False)

    text_input = TextInput(display_text='Enter Water Temperature',
                           name='inputAmount',
                           placeholder='20.00',
                           append=unicode(u'\u00b0' + 'C'))

    input_tbv = TableView(column_names=('Input', 'Value', 'Units'),
                          rows=[('Length', 739, '[ M ]'),
                                ('Diameter', 1.5, '[ M ]'),
                                ('Elevation Head', 135, '[ M ]')],
                          hover=True,
                          striped=True,
                          bordered=True,
                          condensed=True,
                          editable_columns=(False, 'valueInput'),
                          row_ids=[0, 1, 2])

    bends_tbv = TableView(column_names=('Bends', 'Count'),
                          rows=[('90 Smooth (Flanged)', 0),
                                ('90 Smooth (Threaded)', 0),
                                ('90 Miter', 0),
                                ('45 Threaded Elbow', 1),
                                ('Threaded Union', 121)],
                          hover=True,
                          striped=True,
                          bordered=True,
                          condensed=True,
                          editable_columns=(False, 'BCountInput'),
                          row_ids=[0, 1, 2, 3, 4])

    inlets_tbv = TableView(column_names=('Inlets', 'Count'),
                          rows=[('Reentrant', 0),
                                ('Sharp Edge', 1),
                                ('Well-Rounded', 0),
                                ('Slightly-Rounded', 0)],
                          hover=True,
                          striped=True,
                          bordered=True,
                          condensed=True,
                          editable_columns=(False, 'ICountInput'),
                          row_ids=[0, 1, 2, 3])

    exits_tbv = TableView(column_names=('Exit', 'Count'),
                          rows=[('Reentrant (Turb)', 0),
                                ('Sharp Edge (Turb)', 1),
                                ('Rounded (Turb)', 0)],
                          hover=True,
                          striped=True,
                          bordered=True,
                          condensed=True,
                          editable_columns=(False, 'ECountInput'),
                          row_ids=[0, 1, 2])

    gradContraction_tbv = TableView(column_names=('Contraction', 'Count'),
                                    rows=[('30 Degree', 0),
                                          ('45 Degree', 0),
                                          ('60 Degree', 0)],
                                    hover=True,
                                    striped=True,
                                    bordered=True,
                                    condensed=True,
                                    editable_columns=(False, 'GCountInput'),
                                    row_ids=[0, 1, 2])

    submit_button = Button(
                    display_text='Calculate Capacity',
                    name='submit',
                    attributes='form=parameters-form',
                    submit=True
    )

    session.close()

    context = {
        'materialDropdown': materialDropdown,
        'text_input': text_input,
        'input_tbv': input_tbv,
        'bends_tbv': bends_tbv,
        'inlets_tbv': inlets_tbv,
        'exits_tbv': exits_tbv,
        'gradContraction_tbv': gradContraction_tbv,
        'submit_button': submit_button
}

    return render(request, 'storage_capacity/home.html', context)

def resultspage(request):
	"""
	Controller for the app results page.
	"""

	#Get fdc data from main.js file through GET function
	data=request.GET
	flowlist=data['key1']
	print flowlist
	#format flowlist, and split by ,
	flowlist=flowlist[1:-1]
	flowlist_list=flowlist.split(",")
	flow_float=[float(s.encode('ascii')) for s in flowlist_list]
	flow_format=['%.2f' % elem for elem in flow_float]
	#define percentages
	plist=[99,95,90,85,75,70,60,50,40,30,20]
	#zip lists together
	paired_lists=zip(plist,flow_format)
	print paired_lists
	#format for LinePlot
	plot_data=[[float(s) for s in list] for list in paired_lists]



	fdc_tbv=TableView(column_names=('Percent (%)', unicode('Flow (m'+u'\u00b3'+'/s)')),
					rows=paired_lists,
					hover=True,
					striped=True,
					bordered=True,
					condensed=True,
					editable_columns=(False,False,False),
					row_ids=[range(0,10)]
					)

	plot_view=LinePlot(
		height='100%',
		width='200px',
		engine='highcharts',
		title='Flow-Duration Curve',
		subtitle=' ',
		spline=True,
		x_axis_title='Percent',
		x_axis_units='%',
		y_axis_title='Flow',
		y_axis_units='m^3/s',
		series=[{
			'name': 'Flow',
			'color': '#0066ff',
			'marker': {'enabled':False},
			'data': plot_data
		}]

		)
	
	if request.POST and 'submit' in request.POST:
		session=SessionMaker()

		capacityList=[]

		for row in paired_lists:
			flow=row.flow

			pipeMaterial=float(request.POST['materialDropdown'])
			length = float(request.POST['valueInput0'])
			diameter = float(request.POST['valueInput1'])
			elevHead = float(request.POST['valueInput2'])

			density = 998
			kinViscosity = 0.00000112
			turbineEfficiency = 0.53
			gravity = 9.81
			RDRatio = pipeMaterial / diameter
			XSArea = pi * (diameter/2.0)**2
			aveVelocity = flow/XSArea
			reynolsN = (aveVelocity * diameter) / kinViscosity
			flowType = 'Laminar' if reynolsN < 2000 else 'Turbulent'
			massFR = density * flow
			frictionFactor = 64 / reynolsN if flowType == 'Laminar' else (1 / (-1.8 * log10((RDRatio / 3.7)**1.11 + (6.9 / reynolsN))))**2

			smooth90F = 0.3 * float(request.POST['BCountInput0'])
			smooth90T = 0.9 * float(request.POST['BCountInput1'])
			miter90 = 1.1 * float(request.POST['BCountInput2'])
			elbow45T = 0.4 * float(request.POST['BCountInput3'])
			unionT = 0.08 * float(request.POST['BCountInput4'])

			reentrant = 0.8 * float(request.POST['ICountInput0'])
			sharpeEdge = 0.5 * float(request.POST['ICountInput1'])
			wellRounded = 0.03 * float(request.POST['ICountInput2'])
			slightlyRounded = 0.12 * float(request.POST['ICountInput3'])

			reentrantT = 1.05 * float(request.POST['ECountInput0'])
			sharpeEdgeT = 1.05 * float(request.POST['ECountInput1'])
			roundedT = 1.05 * float(request.POST['ECountInput2'])

			degree30 = 0.02 * float(request.POST['GCountInput0'])
			degree45 = 0.04 * float(request.POST['GCountInput1'])
			degree60 = 0.07 * float(request.POST['GCountInput2'])

			totalK = smooth90F + smooth90T + miter90 + elbow45T + unionT + reentrant + sharpeEdge + wellRounded +\
			slightlyRounded + reentrantT + sharpeEdgeT + roundedT + degree30 + degree45 + degree60

			minorLosses = totalK * (aveVelocity**2 / (2 * gravity))
			frictionLoss = (frictionFactor * length * aveVelocity**2) / (diameter * 2 * gravity)

			totalHeadLoss = minorLosses + frictionLoss
			turbineHead = elevHead - totalHeadLoss

			capacity = (turbineHead * density * flow * turbineEfficiency * gravity) / 1000
			apacityList.append((int(row.percent), round(float(flow), 2), round(float(capacity), 2)))
		sortedCapList=sorted(capacityList, key=lambda x:x[0])








	context={'fdc_tbv':fdc_tbv,
			'plot_view':plot_view}
	return render(request, 'storage_capacity/resultspage.html',context)