#!/usr/bin/env python

import sys, copy, os, re

from esm_rcfile import FUNCTION_PATH

import esm_parser


######################################################################################
########################### class "environment_infos" ################################
######################################################################################


class environment_infos:
    def __init__(self, run_or_compile, complete_config = None):

        if not complete_config and not config_from_master:
            # should not happen anymore
            self.machine_file = esm_parser.determine_computer_from_hostname()
            self.config = esm_parser.yaml_file_to_dict(self.machine_file)
            esm_parser.basic_choose_blocks(self.config, self.config)
            esm_parser.recursive_run_function(
                [], self.config, "atomic", esm_parser.find_variable, self.config, [], True
            )
        else:
            self.config = complete_config["computer"]

        for entry in ["add_module_actions", "add_export_vars"]:
            if entry in self.config:
                del self.config[entry]

        self.apply_config_changes(run_or_compile, complete_config)
        self.add_esm_var()
        self.commands = self.get_shell_commands()



    def add_esm_var(self):
        if "export_vars" in self.config:
            self.config["export_vars"] += ["ENVIRONMENT_SET_BY_ESMTOOLS=TRUE"]
        else:
            self.config["export_vars"] = ["ENVIRONMENT_SET_BY_ESMTOOLS=TRUE"]

    def apply_config_changes(self, run_or_compile, config):
        for model in config:
            self.apply_model_changes(model, run_or_compile = run_or_compile, modelconfig = config[model])

    def apply_model_changes(self, model, run_or_compile = "runtime",  modelconfig = None):
        try:
            if not modelconfig:
                # should not happen anymore...
                modelconfig = esm_parser.yaml_file_to_dict(FUNCTION_PATH + "/" + model + "/" + model)
            thesechanges =  run_or_compile + "_environment_changes"
            if thesechanges in modelconfig:
                if "environment_changes" in modelconfig:
                    modelconfig["environment_changes"].update(modelconfig[thesechanges])
                else:
                    modelconfig["environment_changes"] = modelconfig[thesechanges]


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

                esm_parser.basic_choose_blocks(self.config, self.config)

                for entry in ["add_module_actions", "add_export_vars"]:
                    if entry in self.config:
                        del self.config[entry]
        except:
            pass


    def replace_model_dir(self, model_dir):
        for entry in ["export_vars"]:
            if entry in self.config:
                newlist = []
                for line in self.config[entry]:
                    newline = line.replace("${model_dir}", model_dir)
                    newlist.append(newline)
                self.config[entry] = newlist


    def get_shell_commands(self):
        environment = []
        if "module_actions" in self.config:
            for action in self.config["module_actions"]:
                if action.startswith("source"):
                    environment.append(action)
                else:    
                    environment.append("module " + action)
        environment.append("")
        if "export_vars" in self.config:
            for var in self.config["export_vars"]:
                if type(var) == dict:
                    key = list(var.keys())[0]
                    value = var[key]
                    environment.append(
                        "export " + key + "='" + str(value)+"'"
                    )
                else:
                    environment.append(
                        "export " + str(var)
                    )
        return environment


    def write_dummy_script(self):
        with open("dummy_script.sh", "w") as script_file:
            script_file.write(
                "# Dummy script generated by esm-tools, to be removed later: \n"
            )
            script_file.write("set -e\n")
            for command in self.commands:
                script_file.write(command + "\n")
            script_file.write("\n")

    def cleanup_dummy_script(self):
        try:
            os.remove("dummy_script.sh")
        except OSError:
            print("No file dummy_script.sh there; nothing to do...")

    def add_commands(self, commands, name):
        if commands:
            with open(name + "_script.sh", "w") as newfile:
                with open("dummy_script.sh", "r") as dummy_file:
                    newfile.write(dummy_file.read())
                for command in commands:
                    newfile.write(command + "\n")
        return name+"_script.sh"

    def output():
        esm_parser.pprint_config(self.config)
