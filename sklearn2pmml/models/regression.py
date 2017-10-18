try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from . import Model


class RegressionModel(Model):

    def __init__(self, estimator, pmml, function_name, type):
        super(RegressionModel, self).__init__(estimator, pmml, function_name)
        self.type = type

    @property
    def n_features(self):
        return self.estimator.coef_.size

    @property
    def n_classes(self):
        return self.estimator.classes_.size

    @property
    def model(self):
        regression_model = ET.Element('RegressionModel')
        regression_model.set('functionName', self.function_name)
        regression_model.set('modelType', self.type)
        if self.pmml.model_name:
            regression_model.set('modelName', self.pmml.model_name)
        regression_model.append(self.mining_schema)
        if self.function_name == 'classification':
            regression_model.append(self.output)
        regression_table = ET.SubElement(regression_model, 'RegressionTable')
        regression_table.set('intercept', str(self.estimator.intercept_))
        for feature, coefficient in zip(self.pmml.feature_names, self.estimator.coef_.ravel()):
            numeric_predictor = ET.SubElement(regression_table, 'NumericPredictor')
            numeric_predictor.set('name', feature)
            numeric_predictor.set('coefficient', str(coefficient))
        return regression_model
