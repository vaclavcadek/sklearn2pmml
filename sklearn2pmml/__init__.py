try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import _tree
from sklearn.preprocessing import StandardScaler, MinMaxScaler

SUPPORTED_MODELS = frozenset([RandomForestClassifier])
SUPPORTED_TRANSFORMERS = frozenset([StandardScaler, MinMaxScaler])


def _validate_inputs(model, transformer, feature_names, target_values):
    print('[x] Performing model validation.')
    if not type(model) in SUPPORTED_MODELS:
        raise TypeError("Provided model is not supported.")
    if not model.fit:
        raise TypeError("Provide a fitted model.")
    if transformer is not None and not type(transformer) in SUPPORTED_TRANSFORMERS:
        raise TypeError("Provided transformer is not supported.")
    if model.n_features_ != len(feature_names):
        print('[!] Network input shape does not match provided feature names - using generic names instead.')
        feature_names = ['x{}'.format(i) for i in range(model.n_features_)]
    if model.n_classes_ != len(target_values):
        print('[!] Network output shape does not match provided target values - using generic names instead.')
        target_values = ['y{}'.format(i) for i in range(model.n_classes_)]
    print('[x] Model validation successful.')
    return feature_names, target_values


def _generate_header(root, kwargs):
    description = kwargs.get('description', None)
    copyright = kwargs.get('copyright', None)
    header = ET.SubElement(root, 'Header')
    if copyright:
        header.set('copyright', copyright)
    if description:
        header.set('description', description)
    timestamp = ET.SubElement(header, 'Timestamp')
    timestamp.text = str(datetime.now())
    return header


def _generate_data_dictionary(root, feature_names, target_name, target_values):
    data_dict = ET.SubElement(root, 'DataDictionary')
    data_field = ET.SubElement(data_dict, 'DataField')
    data_field.set('name', target_name)
    data_field.set('dataType', 'string')
    data_field.set('optype', 'categorical')
    print('[x] Generating Data Dictionary:')
    for t in target_values:
        value = ET.SubElement(data_field, 'Value')
        value.set('value', t)
    for f in feature_names:
        data_field = ET.SubElement(data_dict, 'DataField')
        data_field.set('name', f)
        data_field.set('dataType', 'double')
        data_field.set('optype', 'continuous')
        print('\t[-] {}...OK!'.format(f))
    return data_dict


def _generate_mining_model(root, estimator, transformer, feature_names, target_name, target_values, model_name=None):
    mining_model = ET.SubElement(root, 'MiningModel')
    mining_model.set('functionName', 'classification')
    if model_name:
        mining_model.set('modelName', model_name)
    _generate_mining_schema(mining_model, feature_names, target_name)
    _generate_output(mining_model, target_values)
    _generate_segmentation(mining_model, estimator, feature_names)
    return mining_model


def _generate_mining_schema(mining_model, feature_names, target_name):
    mining_schema = ET.SubElement(mining_model, 'MiningSchema')
    mining_field = ET.SubElement(mining_schema, 'MiningField')
    if target_name:
        mining_field.set('name', target_name)
        mining_field.set('usageType', 'target')
        for f in feature_names:
            mining_field = ET.SubElement(mining_schema, 'MiningField')
            mining_field.set('name', f)
            mining_field.set('usageType', 'active')
    return mining_schema


def _generate_output(mining_model, target_values):
    output = ET.SubElement(mining_model, 'Output')
    for t in target_values:
        output_field = ET.SubElement(output, 'OutputField')
        output_field.set('name', 'probability_{}'.format(t))
        output_field.set('feature', 'probability')
        output_field.set('value', t)
    return output


def _generate_tree(tree_model, estimator):

    def recurse(tree, node_id, parent, depth=0):
        left_child = tree.children_left[node_id]
        right_child = tree.children_right[node_id]
        for child in [left_child, right_child]:
            node = ET.SubElement(parent, 'Node')
            node.set('id', str(child))
            if child != _tree.TREE_LEAF:
                predicate = ET.SubElement(node, 'SimplePredicate')
                predicate.set('operator', 'lessOrEqual')
                predicate.set('value', str(tree.threshold[child]))
                predicate.set('field', 'field_id')
                recurse(tree, child, node, depth=depth + 1)
            else:
                for target_value, cnt_records in enumerate(tree.value[node_id][0]):
                    score_distribution = ET.SubElement(node, 'ScoreDistribution')
                    score_distribution.set('value', str(target_value))
                    score_distribution.set('recordCount', str(cnt_records))

    root = ET.SubElement(tree_model, 'Node')
    root.set('id', str(0))
    recurse(estimator.tree_, 0, root)
    return root


def _generate_segmentation(mining_model, estimator, feature_names):

    segmentation = ET.SubElement(mining_model, 'Segmentation')
    segmentation.set('multipleModelMethod', 'average')
    for i, e in enumerate(estimator.estimators_):
        segment = ET.SubElement(segmentation, 'Segment')
        segment.set('id', str(i))
        tree_model = ET.SubElement(segment, 'TreeModel')
        _generate_mining_schema(tree_model, feature_names, [])
        _generate_tree(tree_model, e)


def sklearn2pmml(estimator, transformer=None, file=None, **kwargs):
    """
    Exports sklearn model as PMML.

    :param estimator: sklearn model to be exported as PMML (for supported models - see bellow).
    :param transformer: if provided then scaling is applied to data fields.
    :param file: name of the file where the PMML will be exported.
    :param kwargs: set of params that affects PMML metadata - see documentation for details.
    :return: XML element tree
    """

    feature_names = kwargs.get('feature_names', [])
    target_name = kwargs.get('target_name', 'class')
    target_values = kwargs.get('target_values', [])
    model_name = kwargs.get('model_name', None)

    feature_names, target_values = _validate_inputs(estimator, transformer, feature_names, target_values)

    pmml = ET.Element('PMML')
    pmml.set('version', '4.3')
    pmml.set('xmlns', 'http://www.dmg.org/PMML-4_3')
    _generate_header(pmml, kwargs)
    _generate_data_dictionary(pmml, feature_names, target_name, target_values)
    _generate_mining_model(pmml, estimator, transformer, feature_names, target_name, target_values, model_name)

    tree = ET.ElementTree(pmml)
    print('[x] Generation of PMML successful.')
    if file:
        tree.write(file, encoding='utf-8', xml_declaration=True)
    return tree