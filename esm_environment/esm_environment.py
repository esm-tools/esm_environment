#!/usr/bin/env python

import sys, copy, os, re

from esm_rcfile import FUNCTION_PATH

import esm_parser


######################################################################################
########################### class "environment_infos" ################################
######################################################################################


class environment_infos:
    def __init__(self):
        self.machine_file = esm_parser.determine_computer_from_hostname()
        self.config = esm_parser.yaml_file_to_dict(self.machine_file)
        esm_parser.basic_choose_blocks(self.config, self.config)
        esm_parser.recursive_run_function(
            [], self.config, "atomic", esm_parser.find_variable, self.config, [], True
        )
        for entry in ["add_module_actions", "add_export_vars"]:
            if entry in self.config:
                del self.config[entry]

    def add_esm_var(self):
        if "export_vars" in self.config:
            self.config["export_vars"] += ["ENVIRONMENT_SET_BY_ESMTOOLS=TRUE"]
        else:
            self.config["export_vars"] = ["ENVIRONMENT_SET_BY_ESMTOOLS=TRUE"]


    def apply_config_changes(self, config):
        for kind in ["components", "setups"]:
            if kind in config: 
                for model in config[kind]:
                    self.apply_model_changes(model)


    def apply_model_changes(self, model, modelconfig = None):
        try:
            if not modelconfig:
                modelconfig = esm_parser.yaml_file_to_dict(FUNCTION_PATH + "/" + model + "/" + model)            
            if "environment_changes" in modelconfig:
                for entry in ["add_module_actions", "add_export_vars"]:
                    if not entry in self.config:
                        self.config[entry] = []
                    if entry in modelconfig["environment_changes"]:
                        if type(modelconfig["environment_changes"][entry]) == list:
                            self.config[entry] += modelconfig["environment_changes"][entry]
                        else:
                            self.config[entry] += [modelconfig["environment_changes"][entry]]
                        del modelconfig["environment_changes"][entry]
                            
                self.config.update(modelconfig["environment_changes"])
                all_keys = self.config.keys()
                for key in all_keys:
                    if "choose_computer." in key:
                        newkey=key.replace("computer.", "")
                        self.config[newkey] = self.config[key]
                        del self.config[key]

                esm_parser.pprint_config(self.config)

                esm_parser.basic_choose_blocks(self.config, self.config)

                for entry in ["add_module_actions", "add_export_vars"]:
                    if entry in self.config:
                        del self.config[entry]
        except:
            pass



    def write_dummy_script(self):
        with open("dummy_script.sh", "w") as script_file:
            script_file.write(
                "# Dummy script generated by esm-tools, to be removed later: \n"
            )
            if "module_actions" in self.config:
                for action in self.config["module_actions"]:
                    script_file.write("module " + action + "\n")
            script_file.write("\n")
            if "export_vars" in self.config:
                for var in self.config["export_vars"]:
                    script_file.write(
                        "export " + var + "\n"
                    )
            script_file.write("\n")

    def add_commands(self, commands, name):
        with open(name + "_script.sh", "w") as newfile:
            with open("dummy_script.sh", "r") as dummy_file:
                newfile.write(dummy_file.read())
            for command in commands:
                newfile.write(command + "\n")
        return name+"_script.sh"

    def output():
        esm_parser.pprint_config(self.config)